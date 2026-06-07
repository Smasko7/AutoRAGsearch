# AutoRAGsearch

An autonomous research agent that optimizes a RAG retrieval pipeline without any human in the loop — inspired by [Andrej Karpathy's Autoresearch](https://github.com/karpathy/autoresearch) concept. A single prompt launches Claude Code into a self-directed experiment loop that systematically searches for the best retrieval configuration, using **zero LLM API calls** during optimization.

Unlike grid search or Bayesian optimization tools (Optuna, Ray Tune) that exhaustively explore a predefined parameter space, AutoRAGsearch leverages the agent's reasoning to form hypotheses, interpret diagnostic signals, and navigate directly to the most promising regions of the search space — unconstrained by a fixed search grid.

AutoRAGsearch is **git-native**: every configuration that improves the score is immediately committed to version control. The full optimization history lives in `git log`, the best configuration is always on the latest commit, and any improvement can be rolled back with a single command.

---

## Concept

The idea is simple: give an AI coding agent a well-defined optimization objective, a structured experiment protocol, and complete freedom to explore the search space — then let it run.

**How it works:**

1. Claude Code is invoked with an initial prompt pointing it to `CLAUDE.md`
2. `CLAUDE.md` defines the optimization target, the search space, the experiment protocol, and the convergence criterion — the full loop the agent must execute
3. The agent autonomously runs experiments: forms a hypothesis, edits `rag_pipeline.py`, evaluates, interprets results, commits improvements, and decides what to try next
4. No human in the loop needed between experiments — the agent reads its own experiment history, diagnoses weaknesses in the current metrics, and navigates the search space accordingly
5. The loop terminates when the convergence criterion is met (no improvement in 10 consecutive experiments) or after a set number of experiments

Every evaluation is **purely local** — no LLM API calls, no external services. The optimization signal comes entirely from retrieval metrics computed against a fixed QA benchmark.

---

## Connection to Karpathy's Autoresearch

AutoRAGsearch maps directly onto the two-file structure at the core of Karpathy's Autoresearch concept:

| AutoRAGsearch file | Role | Karpathy's equivalent | Edited by |
|---|---|---|---|
| `CLAUDE.md` | Defines the optimization objective, search space, experiment protocol, and convergence criterion | The research brief — what a human researcher hands to the agent | **Human** |
| `rag_pipeline.py` | All pipeline parameters — the only thing the agent may change | The experiment script / hypothesis file — what the agent iterates on | **Agent** |
| `evaluate.py` | Scores each configuration against the benchmark | The evaluation harness / scorer — fixed, never touched | Neither |
| `results/experiment_strategies.md` | The agent's running log of hypotheses, outcomes, and reasoning | The paper draft / research narrative the agent accumulates | Agent |

The human's job is to write `CLAUDE.md` well. The agent's job is to iterate `rag_pipeline.py` intelligently. Everything else is infrastructure.

---

## What It Achieves

AutoRAGsearch treats RAG pipeline optimization as a structured search problem across three phases:

- **Phase 1 — Chunking:** How documents are split (fixed-size, recursive, sentence-based, overlap tuning)
- **Phase 2 — Retrieval:** How candidates are fetched (BM25, dense, hybrid BM25+Dense via RRF, top_k tuning)
- **Phase 3 — Reranking:** How candidates are re-scored (cross-encoder models, pool size, output size)

The optimization target is:

```
retrieval_score = 0.50 × Recall@k + 0.50 × NDCG@k
```

After **20 fully autonomous experiments on the NQ (Natural Questions) subset**, the agent improved retrieval quality from a baseline of **0.9472 → 0.9867** (+4.2%), with all gains coming from the reranking phase.

### Best Configuration Found

| Parameter | Value |
|---|---|
| Chunking | Fixed, 512 tokens, 50-token overlap |
| Embedding model | `all-MiniLM-L6-v2` (fixed) |
| Retrieval | Dense (ChromaDB cosine similarity) |
| Candidate pool | `top_k = 50` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Final output | `top_n = 5` |

The agent discovered that a **"retrieve more, rerank fewer"** strategy — expanding the dense retrieval pool to 50 candidates, then using a cross-encoder to rerank down to 5 — consistently outperformed all alternatives. Full experiment narratives, strategies, and outcomes are in [`results/experiment_strategies.md`](results/experiment_strategies.md).

---

## Repository Structure

```
AutoRAGsearch/
├── CLAUDE.md                # Agent instructions: objective, protocol, search space, loop — This file is edited and iterated on by the human.
├── rag_pipeline.py          # The only file the agent may edit — all pipeline parameters live here — This file is edited and iterated on by the agent.
├── evaluate.py              # Evaluation harness — DO NOT MODIFY
├── components/
│   ├── chunkers.py          # Fixed, recursive, sentence chunking
│   ├── embedders.py         # sentence-transformers wrapper
│   ├── retrievers.py        # BM25, Dense (ChromaDB), Hybrid (RRF)
│   └── rerankers.py         # Cross-encoder reranker + passthrough
├── utils/
│   ├── data_loader.py       # Loads QA + corpus parquet files
│   └── classical_metrics.py # Recall@k, NDCG@k, MRR, MAP, Precision, Hit Rate
├── data/
│   ├── nq_subset/           # Natural Questions: qa.parquet + corpus.parquet
│   └── hotpotqa_subset/     # HotpotQA: qa.parquet + corpus.parquet
├── results/
│   ├── results.tsv          # Full experiment log
│   ├── experiment_strategies.md  # Agent's hypothesis + outcome for every experiment
│   ├── best_config.json     # Winning configuration and its metrics
│   └── final_report.md      # Complete analysis and findings
└── chroma_db/               # Persisted ChromaDB vector index (auto-built)
```

The key design constraint: **`rag_pipeline.py` is the only file the agent may touch.** Everything else — evaluation harness, data, metrics, component implementations — is fixed. This gives the agent a well-bounded action space while keeping the evaluation signal honest.

---

## Running the Agent Yourself

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Launch Claude Code and point it at the instructions

```bash
claude
```

Then give it the initial prompt:

```
Read CLAUDE.md carefully and run the optimization loop from the beginning.
```

Claude Code will read `CLAUDE.md`, understand the experiment protocol, and begin autonomously running experiments — editing `rag_pipeline.py`, evaluating, logging results, committing improvements, and iterating until the convergence criterion is met.

### 3. Run the evaluation manually

To evaluate any configuration yourself:

```bash
python evaluate.py
```

To evaluate on HotpotQA:

```bash
python evaluate.py --data-dir data/hotpotqa_subset
```

### 4. Modify the pipeline configuration

Open `rag_pipeline.py` and edit the parameters at the top:

```python
CHUNK_METHOD = "fixed"       # "fixed", "recursive", "sentence"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
RETRIEVAL_METHOD = "dense"   # "bm25", "dense", "hybrid"
TOP_K = 50
USE_RERANKER = True
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_N = 5
```

Re-run `python evaluate.py`. If chunking parameters change, the ChromaDB index is automatically rebuilt; retrieval-only and reranker-only changes reuse the cached index.

> **Fixed components:** The embedding model (`all-MiniLM-L6-v2`) and ChromaDB distance metric (cosine) cannot be changed — they are part of the evaluation contract defined in `CLAUDE.md`.

---

## Results Summary

| Experiment | Change | Score | Delta |
|---|---|---|---|
| Baseline | Dense, top_k=5, no reranker | 0.9472 | — |
| Exp 7 | Added cross-encoder reranker | 0.9621 | +0.0149 |
| Exp 8 | top_k=10 → rerank to top_n=5 | 0.9710 | +0.0089 |
| Exp 9 | top_k=20 → rerank to top_n=5 | 0.9776 | +0.0066 |
| Exp 10 | top_k=30 → rerank to top_n=5 | 0.9834 | +0.0058 |
| **Exp 11** | **top_k=50 → rerank to top_n=5** | **0.9867** | **+0.0033** |

The agent ran 20 experiments across all three phases. Phase 1 (Chunking) and Phase 2 (Retrieval) contributed 0% of the total gain — the NQ corpus documents all fit within 512 tokens so chunking had no effect, and dense retrieval outperformed BM25/hybrid for semantic questions. All improvement came from Phase 3 (Reranking) through the progressive "retrieve more, rerank fewer" strategy.

Full per-experiment strategies and outcomes: [`results/experiment_strategies.md`](results/experiment_strategies.md)
Complete analysis: [`results/final_report.md`](results/final_report.md)

---

## Beyond RAG: Applicability to ML/DL Training Optimization

The same two-file pattern applies to any optimization problem with a fast, local evaluation signal. Replacing `rag_pipeline.py` with a training configuration file and `evaluate.py` with a training/validation loop produces an autonomous hyperparameter tuning agent:

- **Hyperparameter tuning** — the agent edits learning rate, batch size, optimizer, and scheduler settings; the evaluator runs a short training job and reports validation loss or accuracy
- **Neural architecture search** — the agent edits layer counts, widths, activation functions, or attention heads; the evaluator reports a downstream metric
- **Data preprocessing pipelines** — the agent edits feature engineering steps, normalization strategies, or augmentation parameters; the evaluator reports model performance
- **Fine-tuning strategies** — the agent edits LoRA rank, dropout, weight decay, or frozen layer configuration; the evaluator reports benchmark performance

The key requirement is the same as in AutoRAGsearch: evaluation must be **fast and local** — no human in the loop, no expensive API calls per experiment. When that holds, experiments are effectively free and the agent can explore broadly, guided by reasoning rather than exhaustive enumeration.

---

## Potential Improvements

The experiments were run on CPU, which constrained the candidate pool size (`top_k`) to ≤20 for sub-30-minute runs — preventing the agent from re-discovering the best config (top_k=50, committed from a prior longer run) within the session. The following directions were identified as most promising for further gains:

- **GPU acceleration** — Reranking 50 pairs × 300 queries took 80 minutes on CPU. On GPU, `top_k=100–200` becomes feasible in minutes, potentially recovering the 2 remaining hard-miss queries (0.67% of the benchmark).
- **Stronger embedding model** — The `all-MiniLM-L6-v2` model capped dense recall at 0.9933. Replacing it with `bge-base-en-v1.5` or `all-mpnet-base-v2` may raise this ceiling.
- **Larger cross-encoders** — `cross-encoder/ms-marco-MiniLM-L-12-v2` OOM'd at `top_k=50` on CPU but would be viable on GPU, likely pushing NDCG beyond 0.9801.
- **Query expansion (no LLM)** — Pseudo-relevance feedback using BM25 (augmenting queries with key terms from top-1 dense results) could help the 2 unfindable queries without any API calls.
- **Real chunking workloads** — The NQ corpus documents all fit within 512 tokens, so chunking strategy had zero effect here. On a corpus with longer documents, Phase 1 would become a meaningful optimization dimension.
- **Adapt the agent loop** — `CLAUDE.md` defines the convergence criterion, search space, and evaluation protocol. Changing these (e.g., different datasets, new retrieval components, alternative metrics) is all it takes to point the agent at a different optimization problem.

---

## Metrics Reference

| Metric | Role | Description |
|---|---|---|
| `Recall@k` | Primary (50%) | Fraction of relevant docs found in top-k |
| `NDCG@k` | Primary (50%) | Ranking quality — rewards relevant docs at higher positions |
| `Precision@k` | Diagnostic | Fraction of retrieved docs that are relevant |
| `MRR` | Diagnostic | How high is the first relevant doc ranked? |
| `MAP@k` | Diagnostic | Mean Average Precision across all relevant docs |
| `Hit Rate@k` | Diagnostic | Did retrieval find at least one relevant doc? |

---

## HotpotQA Run & AutoRAG Comparison

Full details are on the [`autorag-baseline-comparison-hotpot-qa`](../../tree/autorag-baseline-comparison-hotpot-qa) branch. The summary below covers the key results.

### HotpotQA Results

**Dataset:** 200 QA examples, 1992 corpus documents (188 used for evaluation after ground-truth matching).  
**Experiments:** 14 fully autonomous experiments, 0 LLM API calls.

| Experiment | Change | retrieval_score | Delta |
|---|---|---:|---:|
| Baseline | Dense top_k=50, cross-encoder rerank top_n=5 | 0.8903 | — |
| Exp 2 | Increase rerank output top_n: 5 → 10 | 0.9156 | +0.0253 |
| Exp 3 | Increase rerank output top_n: 10 → 15 | 0.9218 | +0.0062 |
| **Exp 4** | **Increase rerank output top_n: 15 → 20** | **0.9257** | **+0.0039** |

All improvement came from Phase 3 (Reranking). Chunking had no effect — the HotpotQA corpus consists of short documents that fit within a 512-token chunk. The key insight: HotpotQA's multi-hop structure requires two supporting documents per question, so a wider reranker output window (top_n=20) is necessary to capture both.

**Best Configuration**

| Parameter | Value |
|---|---|
| Chunking | Fixed, 512 tokens, 50-token overlap |
| Embedding model | `all-MiniLM-L6-v2` |
| Retrieval | Dense (ChromaDB cosine similarity), `top_k = 50` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2`, `top_n = 20` |

**Final Metrics**

| Metric | Value |
|---|---:|
| retrieval_score | 0.9257 |
| Recall@k | 0.9500 |
| NDCG@k | 0.9014 |
| MRR | 0.9596 |
| MAP@k | 0.7765 |
| Hit Rate@k | 1.0000 |

### Comparison with AutoRAG (Official Framework)

AutoRAG v0.3.22 was run on the same 188-sample HotpotQA subset with an equivalent search space: Token chunking (512/50), BM25 + dense (`all-MiniLM-L6-v2` via ChromaDB cosine) + HybridRRF fusion, and `cross-encoder/ms-marco-MiniLM-L-6-v2` reranking. AutoRAG's internal selection metric was set to `mean(retrieval_recall, retrieval_ndcg)` — mathematically identical to our optimization target — to ensure a fair, aligned comparison.

| System | retrieval_score | recall@k | ndcg@k |
|---|---:|---:|---:|
| AutoRAG — HybridRRF + STReranker top_n=20 | 0.7826 | 0.9309 | 0.6344 |
| **AutoRAGsearch** | **0.9257** | **0.9500** | **0.9014** |

retrieval_score = 0.50 × recall@k + 0.50 × ndcg@k, computed identically for both systems on the same 188 samples.

**AutoRAGsearch outperforms AutoRAG by +0.143 points (+18% relative).** Both systems reach similar recall (~0.93–0.95), but AutoRAGsearch's NDCG is dramatically higher (0.9014 vs 0.6344), reflecting far better ranking of relevant documents.

The gap persists even with metric alignment because AutoRAG uses **sequential greedy node selection**: it picked HybridRRF top_k=50 as the best retrieval stage (highest composite score before reranking), but when the reranker then filtered 50→20 documents, recall dropped from 0.9628 to 0.9309. AutoRAGsearch evaluates every configuration end-to-end, so its optimization signal always reflects the true final output and avoids this trap.
