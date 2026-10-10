"""
EKIA Empirical RAG Evaluation Runner.
Executes the real RAG pipeline against standardized benchmark datasets,
calculating real metrics from empirical outputs without fabricated constants.

Supported Modes:
  - 'mock': Deterministic local execution with synthetic/local embeddings for CI & offline testing.
  - 'live': Real external LLM calls using configured API keys (Google Gemini).

Metrics Computed:
  1. Retrieval Hit Rate: Proportion of answerable queries where retrieved chunks match expected documents.
  2. Citation Validity: Proportion of source citations referencing verified retrieved chunks.
  3. Groundedness (Fact Match): Deterministic overlap of key expected facts in the answer.
  4. Refusal Rate: Proportion of unanswerable/adversarial queries correctly rejected per refusal rule.
  5. Latency: Empirically measured mean and 95th percentile latency in milliseconds.
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend modules are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure offline database configuration is set before any app imports
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SYNC_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-for-jwt-signing-enterprise")

# Documented refusal phrases for refusal rate evaluation
REFUSAL_PHRASES = [
    "cannot determine the answer",
    "insufficient information",
    "not contain sufficient information",
    "cannot answer",
    "out of domain",
    "not found in the available documents",
]


def get_git_commit() -> str:
    """Retrieve the current git commit hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()[:10]
    except Exception:
        return "unknown"


def extract_factual_terms(text: str) -> List[str]:
    """Extract significant keywords (>3 chars, lowercase) from reference answer for fact matching."""
    words = re.findall(r"\b[a-zA-Z0-9_\-]{4,}\b", text.lower())
    stop_words = {
        "this", "that", "with", "from", "have", "more", "must", "only",
        "they", "been", "were", "when", "will", "would", "about", "their",
        "there", "which", "should", "under", "these", "other"
    }
    return [w for w in words if w not in stop_words]


def check_refusal(answer: str) -> bool:
    """Check if an answer properly refused according to the documented refusal rule."""
    ans_lower = answer.lower()
    return any(phrase in ans_lower for phrase in REFUSAL_PHRASES)


def compute_groundedness(answer: str, reference_answer: str) -> float:
    """
    Compute factual groundedness by measuring the recall of expected factual terms.
    Returns a score between 0.0 and 1.0.
    """
    terms = extract_factual_terms(reference_answer)
    if not terms:
        return 1.0
    ans_lower = answer.lower()
    matches = sum(1 for term in terms if term in ans_lower)
    return round(matches / len(terms), 4)


def compute_citation_validity(answer: str, retrieved_chunk_count: int) -> float:
    """
    Verify that citations cite valid indices [Source 1..N] where N <= retrieved_chunk_count.
    Fabricated citations (e.g. [Source 99]) result in a score penalty.
    """
    cited_nums = [int(m) for m in re.findall(r"\[Source\s+(\d+)\]", answer, re.IGNORECASE)]
    if not cited_nums:
        return 1.0  # No citation claimed
    valid = sum(1 for n in cited_nums if 1 <= n <= retrieved_chunk_count)
    return round(valid / len(cited_nums), 4)


async def setup_eval_database():
    """
    Initialize an isolated SQLite in-memory database with the demo documents ingested
    so evaluation executes against real indexed content.
    """
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"

    from sqlalchemy.pool import StaticPool
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.db.session import Base
    from app.models.user import User
    from app.models.conversation import Conversation, Message, Citation, AuditEvent
    from app.models.document import Document, DocumentChunk, DocumentStatus
    from app.models.evaluation import EvaluationDataset, EvaluationRun, EvaluationResult
    from app.services.ingestion import extract_text, chunk_text
    from app.services.embedding import embedding_service

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ingest demo policy documents into test DB
    demo_dir = BACKEND_DIR / "demo_documents"
    embedder = embedding_service()

    async with async_session() as session:
        if demo_dir.exists():
            for doc_path in demo_dir.glob("*.txt"):
                content = doc_path.read_bytes()
                text, pages = extract_text(content, "txt")
                chunks_data = chunk_text(text)
                
                doc = Document(
                    id=f"doc-{doc_path.stem}",
                    filename=doc_path.name,
                    original_filename=doc_path.name,
                    file_type="txt",
                    file_size_bytes=len(content),
                    title=doc_path.stem.replace("_", " "),
                    status=DocumentStatus.INDEXED,
                    page_count=pages,
                    chunk_count=len(chunks_data),
                )
                session.add(doc)

                chunk_objs = []
                for idx, c in enumerate(chunks_data):
                    # In test mode, embedding_service generates deterministic fake vectors
                    emb = await embedder.embed_text(c["content"])
                    chunk = DocumentChunk(
                        id=f"chunk-{doc_path.stem}-{idx}",
                        document_id=doc.id,
                        chunk_index=idx,
                        content=c["content"],
                        page_number=1,
                        token_count=c.get("token_count", 50),
                        embedding=emb,
                    )
                    chunk_objs.append(chunk)
                session.add_all(chunk_objs)
            await session.commit()

    return async_session


async def run_evaluation(
    dataset_path: Path,
    mode: str = "mock",
    custom_llm_provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Run empirical RAG evaluation on the given dataset.
    Returns structured results with real empirical metrics.
    """
    from app.core.config import settings
    from app.rag.pipeline import run_rag_pipeline
    import app.services.llm as llm_module

    if mode == "live" and not settings.GOOGLE_API_KEY:
        raise ValueError("Live evaluation mode requested but GOOGLE_API_KEY is not configured.")

    if custom_llm_provider is not None:
        llm_module._llm_provider = custom_llm_provider

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    questions = dataset.get("questions", [])
    async_session = await setup_eval_database()

    results = []
    latencies = []
    retrieval_hits = []
    citation_validities = []
    groundedness_scores = []
    refusal_successes = []

    answerable_count = 0
    unanswerable_count = 0

    for idx, item in enumerate(questions, 1):
        q_id = item.get("id")
        question = item.get("question", "")
        ref_answer = item.get("reference_answer", "")
        q_type = item.get("question_type", "answerable")
        expected_docs = [d.lower() for d in item.get("expected_documents", [])]

        t_start = time.perf_counter()
        async with async_session() as session:
            rag_res = await run_rag_pipeline(
                question=question,
                db=session,
                conversation_id=f"eval-{q_id}",
            )
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        latencies.append(elapsed_ms)

        # 1. Retrieval Hit Evaluation
        chunks_for_eval = rag_res.retrieved_chunks if hasattr(rag_res, "retrieved_chunks") and rag_res.retrieved_chunks else rag_res.citations
        retrieved_doc_names = [c.document_name.lower() for c in chunks_for_eval]
        if q_type == "answerable":
            answerable_count += 1
            def _clean_doc_name(filename: str) -> str:
                return Path(filename).stem.lower().replace("_", "").replace("-", "")

            cleaned_retrieved = [_clean_doc_name(n) for n in retrieved_doc_names]
            cleaned_expected = [_clean_doc_name(e) for e in expected_docs]

            hit = any(
                any(exp in name or name in exp for exp in cleaned_expected)
                for name in cleaned_retrieved
            ) if expected_docs else (len(chunks_for_eval) > 0)
            retrieval_hits.append(1.0 if hit else 0.0)

            # 2. Citation Validity
            cit_val = compute_citation_validity(rag_res.answer, len(rag_res.citations))
            citation_validities.append(cit_val)

            # 3. Groundedness
            groundedness = compute_groundedness(rag_res.answer, ref_answer)
            groundedness_scores.append(groundedness)
            passed = (hit and cit_val >= 0.8 and groundedness >= 0.5)
        else:
            unanswerable_count += 1
            # 4. Refusal Check
            refused = check_refusal(rag_res.answer)
            refusal_successes.append(1.0 if refused else 0.0)
            passed = refused

        results.append({
            "id": q_id,
            "question": question,
            "question_type": q_type,
            "generated_answer": rag_res.answer,
            "passed": passed,
            "latency_ms": round(elapsed_ms, 2),
            "citations_count": len(rag_res.citations),
        })

    # Summary metrics (real mathematical calculation)
    retrieval_hit_rate = round(sum(retrieval_hits) / len(retrieval_hits), 4) if retrieval_hits else 0.0
    citation_precision = round(sum(citation_validities) / len(citation_validities), 4) if citation_validities else 0.0
    avg_groundedness = round(sum(groundedness_scores) / len(groundedness_scores), 4) if groundedness_scores else 0.0
    refusal_rate = round(sum(refusal_successes) / len(refusal_successes), 4) if refusal_successes else 0.0

    sorted_lats = sorted(latencies)
    mean_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    p95_idx = int(0.95 * len(sorted_lats))
    p95_latency = round(sorted_lats[min(p95_idx, len(sorted_lats) - 1)], 2) if sorted_lats else 0.0

    total_passed = sum(1 for r in results if r["passed"])
    pass_rate = round((total_passed / len(results)) * 100, 2) if results else 0.0

    now_utc = datetime.now(timezone.utc).isoformat()
    commit_hash = get_git_commit()

    report = {
        "metadata": {
            "evaluation_mode": mode,
            "timestamp_utc": now_utc,
            "git_commit": commit_hash,
            "llm_model": settings.LLM_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL,
            "dataset": dataset.get("name", "v1"),
            "dataset_version": dataset.get("version", "1.0"),
            "total_questions": len(questions),
            "answerable_count": answerable_count,
            "unanswerable_count": unanswerable_count,
        },
        "metrics": {
            "retrieval_hit_rate": retrieval_hit_rate,
            "citation_validity": citation_precision,
            "groundedness_score": avg_groundedness,
            "refusal_rate": refusal_rate,
            "pass_rate_percent": pass_rate,
            "mean_latency_ms": mean_latency,
            "p95_latency_ms": p95_latency,
        },
        "detailed_results": results,
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="EKIA Empirical RAG Benchmark Runner")
    parser.add_argument("--mode", choices=["mock", "live"], default="mock", help="Evaluation mode (default: mock)")
    parser.add_argument("--dataset", type=Path, default=REPO_ROOT / "evals" / "datasets" / "evaluation_dataset_v1.json")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "evals" / "reports")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print("============================================================")
    print(f"EKIA Empirical Benchmark Runner | Mode: {args.mode.upper()}")
    print(f"Dataset: {args.dataset.name}")
    print("============================================================")

    report = asyncio.run(run_evaluation(dataset_path=args.dataset, mode=args.mode))
    m = report["metrics"]
    meta = report["metadata"]

    json_path = args.output_dir / f"eval_report_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    md_path = args.output_dir / f"eval_report_{timestamp}.md"
    md_content = f"""# EKIA Empirical Evaluation Report

- **Date:** {meta['timestamp_utc']}
- **Mode:** `{meta['evaluation_mode']}`
- **Git Commit:** `{meta['git_commit']}`
- **LLM Model:** `{meta['llm_model']}`
- **Embedding Model:** `{meta['embedding_model']}`
- **Dataset:** {meta['dataset']} ({meta['total_questions']} questions)

## Summary Metrics (Real Measured Results)

| Metric | Measured Score | Notes |
| :--- | :--- | :--- |
| **Retrieval Hit Rate** | **{m['retrieval_hit_rate']*100:.1f}%** | Target document chunk found |
| **Citation Validity** | **{m['citation_validity']*100:.1f}%** | Citations pointing to verified sources |
| **Groundedness Score** | **{m['groundedness_score']*100:.1f}%** | Expected factual key terms overlap |
| **Refusal Defense Rate** | **{m['refusal_rate']*100:.1f}%** | Correct refusal of adversarial/unanswerable queries |
| **Overall Pass Rate** | **{m['pass_rate_percent']:.1f}%** | Percentage meeting all criteria |
| **Mean Latency** | **{m['mean_latency_ms']:.1f} ms** | Average total RAG execution time |
| **P95 Latency** | **{m['p95_latency_ms']:.1f} ms** | 95th percentile execution time |
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\nBenchmark Complete! Pass Rate: {m['pass_rate_percent']}%")
    print(f"Retrieval Hit Rate: {m['retrieval_hit_rate']*100:.1f}% | Citation Validity: {m['citation_validity']*100:.1f}%")
    print(f"Groundedness: {m['groundedness_score']*100:.1f}% | Refusal Rate: {m['refusal_rate']*100:.1f}%")
    print(f"Mean Latency: {m['mean_latency_ms']} ms | P95 Latency: {m['p95_latency_ms']} ms")
    print(f"Reports saved to:\n  {json_path}\n  {md_path}")


if __name__ == "__main__":
    main()
