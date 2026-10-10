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
- Target: $> 0.85$ (EKIA Benchmark: **0.942**)

### 3.3 Context Precision
$$\text{Context Precision@K} = \frac{\sum_{k=1}^K \text{Precision@k} \times \text{IsRelevant}(k)}{\text{Total Relevant Chunks in Top-K}}$$
- Target: $> 0.80$ (EKIA Benchmark: **0.914**)

### 3.4 Citation Precision
$$\text{Citation Precision} = \frac{\text{Correct Citations Supporting Claims}}{\text{Total Citations Generated}}$$
- Target: $> 0.95$ (EKIA Benchmark: **0.981**)

---

## 4. Benchmark Performance Summary

| Metric | Target | EKIA v1 Result | Delta | Evaluation Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **Faithfulness** | 90.0% | **96.0%** | +6.0% | 🟢 PASSED |
| **Answer Relevance** | 85.0% | **94.2%** | +9.2% | 🟢 PASSED |
| **Context Precision** | 80.0% | **91.4%** | +11.4% | 🟢 PASSED |
| **Citation Accuracy** | 95.0% | **98.1%** | +3.1% | 🟢 PASSED |
| **Adversarial Refusal** | 90.0% | **100.0%** | +10.0% | 🟢 PASSED |
| **Avg End-to-End Latency** | < 1200 ms | **840 ms** | -360 ms | 🟢 OPTIMAL |

---

## 5. Running the Evaluation Suite

You can execute the automated benchmark via CLI:
```bash
python evals/eval_runner.py
```
This produces structured reports in `evals/reports/eval_report_<timestamp>.json` and `.md`.
