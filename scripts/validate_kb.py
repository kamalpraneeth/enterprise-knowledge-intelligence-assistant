#!/usr/bin/env python3
"""
Enterprise Knowledge Base Validation Script (scripts/validate_kb.py).
Validates document quality, metadata integrity, size constraints,
duplicate identifiers, and TF-IDF semantic near-duplicates before RAG ingestion.
"""
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


MIN_FILE_SIZE_BYTES = 50
MIN_WORD_COUNT = 10
DEFAULT_SIMILARITY_THRESHOLD = 0.85


def check_metadata(text: str, filename: str) -> List[str]:
    """Verify that document contains minimum required enterprise metadata / structure."""
    errors = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return [f"{filename}: File contains no readable text content."]

    first_few_lines = " ".join(lines[:5]).lower()
    has_header = (
        lines[0].startswith("#")
        or "policy" in first_few_lines
        or "guideline" in first_few_lines
        or "handbook" in first_few_lines
        or "procedure" in first_few_lines
        or "title:" in first_few_lines
        or "overview" in first_few_lines
    )
    if not has_header:
        errors.append(
            f"{filename}: Missing required metadata/header (expected title or policy classification in first 5 lines)."
        )
    return errors


def validate_single_document(
    content: str,
    filename: str,
    file_size_bytes: int,
) -> Tuple[bool, List[str]]:
    """Validate a single document against size, word count, and enterprise metadata constraints."""
    errors = []
    if file_size_bytes < MIN_FILE_SIZE_BYTES:
        errors.append(
            f"{filename}: File is too small ({file_size_bytes} bytes, minimum is {MIN_FILE_SIZE_BYTES} bytes)."
        )
    word_count = len(content.split())
    if word_count < MIN_WORD_COUNT:
        errors.append(
            f"{filename}: Word count too low ({word_count} words, minimum is {MIN_WORD_COUNT} words)."
        )
    errors.extend(check_metadata(content, filename))
    return len(errors) == 0, errors



def validate_knowledge_base(
    directory_path: Path,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Tuple[bool, List[str]]:
    """
    Validate all text and policy documents within a directory.
    
    Checks:
    1. Empty or tiny files (< 50 bytes or < 10 words)
    2. Missing required metadata headers
    3. Duplicate IDs or normalized filenames
    4. Near-duplicate content via TF-IDF cosine similarity
    
    Returns (is_valid: bool, errors: List[str]).
    """
    errors: List[str] = []
    dir_path = Path(directory_path)

    if not dir_path.exists() or not dir_path.is_dir():
        return False, [f"Directory not found: {dir_path}"]

    doc_files = sorted(
        [p for p in dir_path.glob("*.*") if p.suffix.lower() in [".txt", ".md", ".pdf"]]
    )

    if not doc_files:
        return False, [f"No supported knowledge base documents (.txt, .md, .pdf) found in {dir_path}"]

    # 1. Size, word count, and metadata checks
    file_texts: Dict[str, str] = {}
    seen_ids: Dict[str, str] = {}

    for doc_path in doc_files:
        file_size = doc_path.stat().st_size
        filename = doc_path.name

        # Check duplicate normalized IDs/stems
        clean_stem = doc_path.stem.lower().replace("_", "").replace("-", "")
        if clean_stem in seen_ids:
            errors.append(
                f"Duplicate document identifier: '{filename}' conflicts with existing '{seen_ids[clean_stem]}'."
            )
        else:
            seen_ids[clean_stem] = filename

        # Check empty or tiny file
        if file_size < MIN_FILE_SIZE_BYTES:
            errors.append(
                f"{filename}: File is too small ({file_size} bytes, minimum is {MIN_FILE_SIZE_BYTES} bytes)."
            )
            continue

        try:
            content = doc_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            errors.append(f"{filename}: Failed to read file content: {str(e)}")
            continue

        word_count = len(content.split())
        if word_count < MIN_WORD_COUNT:
            errors.append(
                f"{filename}: Word count too low ({word_count} words, minimum is {MIN_WORD_COUNT} words)."
            )

        meta_errs = check_metadata(content, filename)
        errors.extend(meta_errs)

        file_texts[filename] = content

    # 2. Near-duplicate detection using TF-IDF
    valid_filenames = list(file_texts.keys())
    if len(valid_filenames) >= 2:
        corpus = [file_texts[fn] for fn in valid_filenames]
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(corpus)
            sim_matrix = cosine_similarity(tfidf_matrix)

            n = len(valid_filenames)
            for i in range(n):
                for j in range(i + 1, n):
                    sim_score = sim_matrix[i, j]
                    if sim_score >= similarity_threshold:
                        pct = round(sim_score * 100, 1)
                        errors.append(
                            f"Near-duplicate content detected: '{valid_filenames[i]}' and '{valid_filenames[j]}' "
                            f"have {pct}% TF-IDF similarity (threshold: {similarity_threshold * 100}%)."
                        )
        except Exception as e:
            errors.append(f"TF-IDF similarity calculation failed: {str(e)}")

    is_valid = len(errors) == 0
    return is_valid, errors


def main():
    parser = argparse.ArgumentParser(description="Validate EKIA knowledge base documents before ingestion.")
    parser.add_argument("directory", type=Path, help="Path to documents directory")
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
        help=f"Cosine similarity threshold for near-duplicates (default: {DEFAULT_SIMILARITY_THRESHOLD})",
    )
    args = parser.parse_args()

    print(f"Validating Knowledge Base at: {args.directory}")
    is_valid, errors = validate_knowledge_base(
        directory_path=args.directory,
        similarity_threshold=args.similarity_threshold,
    )

    if is_valid:
        print("[SUCCESS] Knowledge base passed all quality and governance validation checks.")
        sys.exit(0)
    else:
        print(f"[FAILED] Knowledge base validation failed with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        print("\nIngestion blocked until errors are resolved.")
        sys.exit(1)


if __name__ == "__main__":
    main()
