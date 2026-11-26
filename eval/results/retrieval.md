# Retrieval ablation

30 golden questions: 13 dev + 12 test positives, 5 negatives. Metrics are over releases (entry_ids). alpha=0.5 was chosen on dev only.

| Config | Recall@5 dev | Recall@5 test | Recall@10 all | MRR all | Wrong-version@10 | p95 s |
|---|---|---|---|---|---|---|
| BM25 (raw text) | 0.63 | 0.63 | 0.71 | 0.56 | 48% | 0.00 |
| BM25 (camelCase split) | 0.68 | 0.63 | 0.73 | 0.62 | 41% | 0.00 |
| Dense, fixed 200-word chunks | 0.37 | 0.55 | 0.60 | 0.49 | 41% | 0.02 |
| Dense, no query prefix | 0.49 | 0.65 | 0.73 | 0.58 | 36% | 0.02 |
| Dense | 0.56 | 0.68 | 0.69 | 0.64 | 39% | 0.02 |
| Hybrid, our RRF | 0.72 | 0.61 | 0.81 | 0.68 | 36% | 0.02 |
| Hybrid, Weaviate alpha=0.0 | 0.68 | 0.63 | 0.73 | 0.62 | 41% | 0.02 |
| Hybrid, Weaviate alpha=0.25 | 0.76 | 0.67 | 0.80 | 0.69 | 38% | 0.02 |
| Hybrid, Weaviate alpha=0.5 | 0.79 | 0.63 | 0.77 | 0.71 | 37% | 0.02 |
| Hybrid, Weaviate alpha=0.75 | 0.72 | 0.65 | 0.75 | 0.68 | 38% | 0.02 |
| Hybrid, Weaviate alpha=1.0 | 0.56 | 0.68 | 0.69 | 0.64 | 39% | 0.02 |
| Dense + library/version filter | 0.79 | 0.83 | 0.89 | 0.76 | 0% | 0.02 |
| Hybrid, our RRF + filter | 0.87 | 0.79 | 0.91 | 0.79 | 0% | 0.02 |
| Hybrid alpha=0.5 + filter | 0.91 | 0.83 | 0.91 | 0.80 | 0% | 0.02 |
| Hybrid alpha=0.5 + filter + rerank | 0.92 | 0.89 | 0.98 | 0.84 | 0% | 2.72 |

## Negative questions

'empty' = the filter left nothing to retrieve (correct refusal for free). Otherwise: top score (rerank logit for the rerank config, search score for others).

| Config | q10 | q20 | q21 | q22 | q23 |
|---|---|---|---|---|---|
| BM25 (raw text) | 6.36 | 6.38 | 5.43 | 5.04 | 5.61 |
| BM25 (camelCase split) | 7.04 | 7.97 | 5.40 | 9.32 | 5.69 |
| Dense, fixed 200-word chunks | 0.74 | 0.74 | 0.70 | 0.78 | 0.64 |
| Dense, no query prefix | 0.83 | 0.82 | 0.75 | 0.85 | 0.69 |
| Dense | 0.77 | 0.76 | 0.71 | 0.80 | 0.66 |
| Hybrid, our RRF | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 |
| Hybrid, Weaviate alpha=0.0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Hybrid, Weaviate alpha=0.25 | 0.89 | 0.96 | 0.75 | 0.84 | 1.00 |
| Hybrid, Weaviate alpha=0.5 | 0.92 | 0.93 | 0.58 | 0.84 | 1.00 |
| Hybrid, Weaviate alpha=0.75 | 0.95 | 0.94 | 0.79 | 0.92 | 1.00 |
| Hybrid, Weaviate alpha=1.0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Dense + library/version filter | 0.77 | 0.76 | empty | 0.80 | empty |
| Hybrid, our RRF + filter | 0.03 | 0.03 | empty | 0.03 | empty |
| Hybrid alpha=0.5 + filter | 0.93 | 0.94 | empty | 0.84 | empty |
| Hybrid alpha=0.5 + filter + rerank | 1.00 | 0.64 | empty | 0.87 | empty |
