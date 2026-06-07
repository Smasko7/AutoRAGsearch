# AutoRAGsearch — HotpotQA Run & AutoRAG Comparison

## Overview

AutoRAGsearch is an autonomous agent that optimizes a RAG retrieval pipeline through self-directed experiments, using **zero LLM API calls** during optimization. This document covers the HotpotQA benchmark run and its comparison against the official AutoRAG framework.

The optimization target is:

```
retrieval_score = 0.50 × Recall@k + 0.50 × NDCG@k
```

---

## HotpotQA Results

**Dataset:** 200 QA examples, 1992 corpus documents (188 used for evaluation after ground-truth matching).
**Experiments:** 14 fully autonomous experiments, 0 LLM API calls.

| Experiment | Change | retrieval_score | Delta |
|---|---|---:|---:|
| Baseline | Dense top_k=50, cross-encoder rerank top_n=5 | 0.8903 | — |
| Exp 2 | Increase rerank output top_n: 5 → 10 | 0.9156 | +0.0253 |
| Exp 3 | Increase rerank output top_n: 10 → 15 | 0.9218 | +0.0062 |
| **Exp 4** | **Increase rerank output top_n: 15 → 20** | **0.9257** | **+0.0039** |

All improvement came from Phase 3 (Reranking). Chunking had no effect — the HotpotQA corpus consists of short documents that fit within a 512-token chunk. Retrieval-method changes (BM25, hybrid, larger dense pools) yielded no gains. The key insight: HotpotQA's multi-hop structure requires two supporting documents per question, so a wider reranker output window (top_n=20) is necessary to capture both.

### Best Configuration

| Parameter | Value |
|---|---|
| Chunking | Fixed, 512 tokens, 50-token overlap |
| Embedding model | `all-MiniLM-L6-v2` |
| Retrieval | Dense (ChromaDB cosine similarity), `top_k = 50` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2`, `top_n = 20` |

### Final Metrics

| Metric | Value |
|---|---:|
| retrieval_score | 0.9257 |
| Recall@k | 0.9500 |
| NDCG@k | 0.9014 |
| MRR | 0.9596 |
| MAP@k | 0.7765 |
| Hit Rate@k | 1.0000 |

Full per-experiment strategies and outcomes: [`results/experiment_strategies.md`](results/experiment_strategies.md)
Complete analysis: [`results/final_report.md`](results/final_report.md)

---

## Comparison with AutoRAG (Official Framework)

AutoRAG v0.3.22 was run on the same 188-sample HotpotQA subset with an equivalent search space: Token chunking (512/50), BM25 + dense (`all-MiniLM-L6-v2` via ChromaDB cosine) + HybridRRF fusion, and `cross-encoder/ms-marco-MiniLM-L-6-v2` reranking. top_k ∈ {20, 50}, hybrid fusion weights (4–80), and rerank_top_n ∈ {10, 20} were explored. AutoRAG's internal selection metric was set to `mean(retrieval_recall, retrieval_ndcg)` — mathematically identical to our optimization target — to ensure a fair, aligned comparison.

| System | retrieval_score | recall@k | ndcg@k |
|---|---:|---:|---:|
| AutoRAG — HybridRRF + STReranker top_n=20 | 0.7826 | 0.9309 | 0.6344 |
| **AutoRAGsearch** | **0.9257** | **0.9500** | **0.9014** |

retrieval_score = 0.50 × recall@k + 0.50 × ndcg@k, computed identically for both systems on the same 188 samples.

**AutoRAGsearch outperforms AutoRAG by +0.143 points (+18% relative).** Both systems reach similar recall (~0.93–0.95), but AutoRAGsearch's NDCG is dramatically higher (0.9014 vs 0.6344), reflecting far better ranking of relevant documents.

The gap persists even with metric alignment because AutoRAG uses **sequential greedy node selection**: it picked HybridRRF top_k=50 as the best retrieval stage (highest composite score before reranking), but when the reranker then filtered 50→20 documents, recall dropped from 0.9628 to 0.9309. AutoRAGsearch evaluates every configuration end-to-end, so its optimization signal always reflects the true final output and avoids this trap.

Configuration files, conversion scripts, and full result parquets for the AutoRAG comparison are in [`experiments/official_autorag_baseline/`](experiments/official_autorag_baseline/). A detailed analysis is in [`results/final_report.md`](results/final_report.md).

### Reproducing the AutoRAG Comparison

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

> `AutoRAG[gpu]` is **not** required. The base `AutoRAG==0.3.22` plus `llama-index-embeddings-huggingface` is sufficient. `[gpu]` only adds vllm and other unneeded extras and has a broken pip resolver as of this writing.

**2. Pre-download the models** (needed only once; skip if already cached)

```bash
python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

**3. Convert the HotpotQA dataset to AutoRAG format**

```bash
python experiments/official_autorag_baseline/convert_my_hotpotqa_subset.py
```

This produces `experiments/official_autorag_baseline/data/my_hotpotqa_subset_autorag/` with `qa_validation.parquet` and `corpus.parquet`.

**4. Run the comparison**

```bash
python experiments/official_autorag_baseline/run_autorag_comparison.py
```

The script auto-discovers the locally cached model snapshot, resolves all paths relative to its own location, sets `HF_HUB_OFFLINE=1` to skip network calls, and writes results to `experiments/official_autorag_baseline/autorag_fair_result_v2/`.

> **SSL note:** If your machine has SSL certificate verification issues (common in corporate/university networks), pre-downloading the models in step 2 is essential. The wrapper script forces offline mode, so no HTTPS calls are made during the AutoRAG run itself.
