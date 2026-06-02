# AutoRAGsearch Final Report

## Overview

- **Dataset**: hotpotqa_subset (200 QA samples, 1992 corpus documents)
- **Evaluation**: retrieval_score = 0.50 * recall@k + 0.50 * ndcg@k
- **Total experiments**: 24 (0 LLM calls)
- **Baseline retrieval_score**: 0.8387
- **Final retrieval_score**: 0.9288
- **Total improvement**: +0.0901 (+10.7%)

---

## Experiments Per Phase

| Phase | Experiments | Count |
|-------|------------|-------|
| 1-Chunking | 1, 14, 15 | 3 |
| 2-Retrieval | 2, 3, 4, 11, 16, 18, 19, 20, 21, 22, 23, 24 | 12 (incl. 1 crash, 2 procedural) |
| 3-Reranking | 5, 6, 7, 8, 9, 10, 12, 13, 17 | 9 |

---

## Best Configuration

| Parameter | Value |
|-----------|-------|
| chunk_method | fixed |
| chunk_size | 512 words |
| chunk_overlap | 256 words |
| embedding_model | all-MiniLM-L6-v2 |
| retrieval_method | dense |
| top_k | 50 |
| use_reranker | True |
| reranker_model | cross-encoder/ms-marco-MiniLM-L-12-v2 |
| rerank_top_n | 50 |
| distance_metric | cosine |

---

## Score Progression (Kept Improvements Only)

| Exp | Description | Score | Delta |
|-----|------------|-------|-------|
| 1 | Baseline: dense k=5, no reranker | 0.8387 | (baseline) |
| 3 | Dense k=10, no reranker | 0.8741 | +0.0354 |
| 4 | Dense k=20, no reranker | 0.8861 | +0.0119 |
| 5 | Dense k=20, L-6-v2 reranker | 0.9137 | +0.0276 |
| 6 | Dense k=30, L-6-v2 reranker | 0.9244 | +0.0107 |
| 7 | Dense k=40, L-6-v2 reranker | 0.9264 | +0.0020 |
| 8 | Dense k=50, L-6-v2 reranker | 0.9285 | +0.0021 |
| 13 | Dense k=50, L-12-v2 reranker | 0.9288 | +0.0003 |
| 14 | chunk_overlap=256 (noise-level) | 0.9288 | +0.0001 |

---

## Primary Metric Evolution

| Exp | recall@k | ndcg@k | score |
|-----|----------|--------|-------|
| 1 (baseline) | 0.7850 | 0.8923 | 0.8387 |
| 3 | 0.8825 | 0.8657 | 0.8741 |
| 4 | 0.9225 | 0.8496 | 0.8861 |
| 5 | 0.9225 | 0.9049 | 0.9137 |
| 6 | 0.9450 | 0.9037 | 0.9244 |
| 7 | 0.9550 | 0.8978 | 0.9264 |
| 8 | 0.9600 | 0.8971 | 0.9285 |
| 13 (final) | 0.9600 | 0.8976 | 0.9288 |

---

## Diagnostic Metric Insights

| Metric | Baseline | Final | Change |
|--------|----------|-------|--------|
| precision@k | 0.3140 | 0.0384 | -0.276 (expected: more docs, same relevant) |
| mrr | 0.8933 | 0.9652 | +0.072 (reranker pushes 1st relevant to rank 1) |
| map@k | 0.6577 | 0.7768 | +0.119 (2nd relevant doc ranked higher) |
| hit_rate@k | 0.9950 | 1.0000 | +0.005 (all queries find >=1 relevant doc) |

Key insight: MRR and MAP improved dramatically with the reranker, confirming it
correctly promotes both relevant docs toward the top of the ranked list.

---

## Phase Contribution Analysis

| Phase | Score Gain | % of Total |
|-------|-----------|-----------|
| Phase 1 (Chunking) | +0.0001 (noise) | 0.1% |
| Phase 2 (Retrieval, k expansion) | +0.0474 (0.8387->0.8861) | 52.6% |
| Phase 3 (Reranking) | +0.0427 (0.8861->0.9288) | 47.4% |

Phase 2 (k expansion) and Phase 3 (reranking) contributed nearly equally.
Phase 1 (chunking) had zero meaningful effect: the hotpotqa_subset corpus consists
of short Wikipedia paragraphs (avg 102 words), so chunk_size=512 words ensures
1 chunk per document for 99.8% of docs. All chunking variations were irrelevant.

---

## Top 3 Most Impactful Experiments

1. **Exp 3 (+0.0354)**: Expanding TOP_K from 5 to 10 (with RERANK_TOP_N=10 fixed).
   HotpotQA requires finding 2 relevant docs per query -- k=5 only captured both for
   ~57.5% of queries. Expanding to k=10 improved recall from 0.785 to 0.8825.

2. **Exp 5 (+0.0276)**: Adding the cross-encoder reranker (L-6-v2) at k=20. The
   reranker pushed NDCG from 0.8496 to 0.9049 (+0.055) by correctly ranking both
   relevant docs near positions 1-2. MRR jumped from 0.8933 to 0.9546.

3. **Exp 4 (+0.0119)**: Expanding k from 10 to 20 (no reranker). Recall improved
   +0.04 (0.8825->0.9225) by giving more room for the second relevant document.

---

## Key Dataset Insights

1. **Multi-hop nature**: HotpotQA requires 2 relevant supporting passages per question.
   Recall is inherently harder than single-hop datasets (NQ), requiring both passages
   to appear in the retrieved set.

2. **Dense recall ceiling**: The all-MiniLM-L6-v2 model reaches a hard ceiling of
   recall=0.9600 at k=50. The 4% hard-miss queries have their second relevant passage
   beyond position 60 in dense ranking -- multi-hop bridge passages are semantically
   distant from the original question.

3. **Reranker critical for NDCG**: Without the reranker, NDCG@k degrades as k grows
   (noise dilutes ranking). The cross-encoder recovers NDCG by sorting 50 candidates
   correctly, raising NDCG from 0.8496 (k=20, no reranker) to 0.9049 (k=20, reranker).

4. **BM25 and Hybrid unusable**: BM25 standalone achieves recall=0.8825 (<dense 0.9600).
   Hybrid retrieval produces a measurement artifact (recall>1.0) from duplicate doc_ids.

5. **Chunking irrelevant**: Average corpus doc is 102 words, well under 512-word chunk
   limit. All Phase 1 experiments produced identical results.

---

## Recommendations for Further Optimization

1. **Better embedding model**: Replace all-MiniLM-L6-v2 with a larger model
   (BAAI/bge-large-en-v1.5, intfloat/e5-large-v2) to raise the dense recall ceiling
   beyond 0.96. This is the single largest remaining bottleneck.

2. **Iterative multi-hop retrieval**: Implement a 2-step pipeline: retrieve top-k for
   the original question, then re-query with question+retrieved-doc context to find
   bridge passages. This directly addresses the multi-hop challenge.

3. **Fix evaluation deduplication**: The metric implementation double-counts duplicate
   doc_ids when a document has >1 chunk. Fixing this enables proper hybrid experiments.

4. **Stronger reranker**: A larger model like cross-encoder/ms-marco-electra-base could
   further improve NDCG. The L-12-v2 showed only marginal gains (+0.0003 score)
   over L-6-v2, suggesting the MiniLM architecture is the binding constraint.
