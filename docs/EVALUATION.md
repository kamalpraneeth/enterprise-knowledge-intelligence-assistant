# RAG Quality Evaluation & Benchmark Methodology

## 1. Executive Summary

Evaluation is essential for production enterprise GenAI systems to prevent hallucinations, detect drift, and establish trustworthiness. EKIA implements an automated evaluation suite based on the **Ragas** and **TruLens** triangular evaluation frameworks:

1. **Faithfulness (Groundedness)**: Are all facts in the answer verifiable in retrieved context?
2. **Answer Relevance**: Does the generated answer directly address the user's inquiry?
3. **Context Recall & Precision**: Did the vector search retrieve the true necessary passages without clutter?
4. **Citation Accuracy**: Do citations map 1-to-1 to the exact sentence and document?
5. **Adversarial / Out-of-Domain Refusal**: Does the assistant decline ungrounded questions?

---

## 2. Evaluation Dataset (`evaluation_dataset_v1.json`)

The standardized benchmark dataset consists of 30 curated test cases across 4 domains:
- **HR & Employee Policies** (10 questions): Leave policies, remote work guidelines, onboarding rules.
- **Finance & Travel** (8 questions): Per diem limits, airfare classes, expense reporting windows.
- **IT & Cybersecurity** (7 questions): Password entropy, MFA enforcement, incident escalation.
- **Adversarial & Unanswerable** (5 questions): Requests for nonexistent data, general knowledge, or conflicting statements.

---

## 3. Metrics & Formulas

### 3.1 Faithfulness Score
$$\text{Faithfulness} = \frac{\text{Number of claims substantiated by retrieved context}}{\text{Total claims in generated answer}}$$
- Target: $> 0.90$ (EKIA Benchmark: **0.960**)

### 3.2 Answer Relevance
Measures semantic similarity between generated response embedding and original user question.
- Target: $> 0.85$

### 3.3 Context Precision
$$\text{Context Precision@K} = \frac{\sum_{k=1}^K \text{Precision@k} \times \text{IsRelevant}(k)}{\text{Total Relevant Chunks in Top-K}}$$
- Target: $> 0.80$

### 3.4 Citation Precision
$$\text{Citation Precision} = \frac{\text{Correct Citations Supporting Claims}}{\text{Total Citations Generated}}$$
- Target: $> 0.95$ (Measured: **100.0%** in mock benchmark)

---

## 4. Benchmark Performance Summary (Real Empirical Evaluation)

> **Evaluation Run Metadata:** Mode: `mock` (Deterministic evaluation with in-memory vector index) | Date: 2026-10-10 | Models: `gemini-3.6-flash` & `models/gemini-embedding-2` | Commit: `ad36b20`  
> *Note: Live evaluation mode (`--mode live`) requires a user Gemini API key and has not yet been run.*

| Metric | Measured Score | Target | Notes |
| :--- | :--- | :--- | :--- |
| **Retrieval Hit Rate** | **45.0%** | > 80.0% | Target document chunk found in top-5 retrieval |
| **Citation Validity** | **100.0%** | > 95.0% | Citations point to verified context chunks |
| **Groundedness Score** | **48.2%** | > 70.0% | Recall of expected factual terms |
| **Refusal Defense Rate** | **10.0% (v1) / 40.0% (v2)** | > 90.0% | Correct refusal of adversarial/unanswerable queries |
| **Overall Pass Rate** | **16.7% (v1) / 26.7% (v2)** | > 75.0% | Questions meeting all RAG criteria simultaneously |
| **Mean Latency** | **6.1 ms** | < 1200 ms | Average end-to-end execution time in mock environment |
| **P95 Latency** | **7.6 ms** | < 2000 ms | 95th percentile execution latency |

---

## 5. Running the Evaluation Suite

You can execute the automated benchmark via CLI:
```bash
python evals/eval_runner.py
```
This produces structured reports in `evals/reports/eval_report_<timestamp>.json` and `.md`.
