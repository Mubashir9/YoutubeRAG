# YouTube RAG experiments

This is a standalone notebook workspace for the retrieval experiments in
[`EXPERIMENTATION_BRIEF.md`](../EXPERIMENTATION_BRIEF.md). It does not run
through the product query path.

## Layout

- `notebooks/` — experiment narratives and controlled comparisons.
- `src/` — small reusable experiment-only helpers.
- `evaluation/` — versioned questions and source evidence labels.
- `notes/` — input provenance, run decisions, and findings.
- `artifacts/DPqiIzK97K0/` — local raw and processed corpus plus the video-only
  local indexes. This path is ignored by Git.
- `outputs/` — generated run tables, figures, and executed notebook copies.
  This path is ignored by Git.

Keep corpus snapshots and indexes here, separate from product data and indexes.
Do not commit full transcript copies, local indexes, generated caches, or
secrets. Commit reviewed, concise notes, evaluation labels, notebooks, and
selected portable results when appropriate.

Phase notes and artifacts:

- [Phase 0 baseline and provenance](notes/phase-0-baseline.md)
- [Phase 1 question set](evaluation/questions-v1.json) and
  [label review](notes/phase-1-label-review.md)
- [Phase 2 baseline notebook](notebooks/baseline-retrieval.ipynb) and
  [run record](notes/phase-2-baseline-run.md)
