# Phase 2 — baseline notebook run

## Notebook and method

[`../notebooks/baseline-retrieval.ipynb`](../notebooks/baseline-retrieval.ipynb)
is the clean, outputs-free notebook entry point. An executed copy and portable
JSON/CSV outputs are kept locally under ignored `experimentation/outputs/`.
The notebook builds the 200 target / 35 overlap / 300 maximum word chunks,
indexes them in a video/config-specific Chroma path, then runs the current
dense plus lexical reciprocal-rank fusion strategy. Dense candidate depth is
20; lexical candidates include all chunks with nonzero scores; RRF constant is
60 with dense weight 1 and lexical weight 2; `k=5`. No generation model/API is
used.

The run record captures the corpus, validated segment and evaluation hashes,
configuration, repository revision, date, dependency versions, Python/runtime
platform, index path, chunking statistics and timing measurements. The JSON
artifact includes each question's ranking, metric inputs, relevant chunk IDs,
and per-question latency. The compact CSV contains the per-question score
table.

## First observed run

Run ID: `baseline-d32421b083cc`  
Run date: 2026-10-19  
Repository revision: `2f3ca4139137b021fa80387e813ff539b364814d`

| Measure | Observed value |
| --- | ---: |
| Answerable questions scored | 21 |
| Hit@5 | 0.762 |
| Recall@5 | 0.738 |
| MRR | 0.623 |
| Timestamp overlap rate@5 | 0.762 |
| Chunk count | 725 |
| Mean chunk words | 203.44 |
| Maximum chunk words | 210 |
| Indexing time | See run JSON; rough single measurement |
| Retrieval latency median / p95 | 0.123 / 0.246 seconds |

Latency uses one retrieval per question in a single pass and is rough. It
includes query embedding and local retrieval on the recorded Windows 11 / Intel
hardware. Aggregate values are descriptive for this one transcript and 21
scored questions. q13 is ambiguous and excluded; three unanswerable questions
are retained in per-question output but excluded from answerable retrieval
metrics. These results measure evidence ranking, not answer confidence.

The notebook completed and wrote actual rankings/metrics; no placeholder scores
were used. A second clean execution produced identical per-question ranking and
metric tables. Timing fields varied as expected. These results are a
reference for controlled chunking/retrieval comparisons, not a product-default
recommendation.
