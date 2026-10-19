# Phase 0 — baseline inputs and configuration

## Corpus identity and provenance

- Video: `DPqiIzK97K0`
- Source: [YouTube video](https://www.youtube.com/watch?v=DPqiIzK97K0)
- Captured language/type: English, auto-generated captions
- Acquisition record: `artifacts/DPqiIzK97K0/raw/DPqiIzK97K0.meta.json`
- Raw caption records: 15,505
- Validation: 15,502 retained, 3 marker-only captions removed, 119,519
  retained words; no validation warnings.
- Caption timeline: 0.199–37,736.96 seconds (about 10 hours 29 minutes).
- Raw JSON SHA-256: `9e3275e1fec88de4fb0440e51e53c6951cb85cd5b6bb7eb205cfde345dfd9952`
- Validated segments JSONL SHA-256:
  `5f02ff99f83854213c547d373a967d9bbee4a718ac97de1c70cfb3f84c3a47e76`
- Existing baseline chunks JSONL SHA-256:
  `43a5bf956b1e0ca3378d38e28815b8760bd257002bf96300beb386b4040cbf95`

The raw and processed files live under the ignored, video-specific
`experimentation/artifacts/DPqiIzK97K0/` path. The captions are the fixed input
snapshot; use the raw-file hash to detect any change. The validated segment
IDs are original caption record indexes and remain the stable source references
for future labels. Chunk IDs are generated and must not be used as gold labels.

## Preparation revision and isolation

- Repository revision when this note was prepared: `2f3ca4139137b021fa80387e813ff539b364814d`.
- The source snapshot and existing chunks were present at this revision; the
  current Phase 0 workspace note/layout is being added as a follow-up change.
- Existing local index: `artifacts/DPqiIzK97K0/index/`, a Chroma index in the
  same ignored, video-specific artifact directory. It is local/rebuildable and
  is not a product index or a tracked deliverable.
- The repository product defaults are not modified by this experiment.

## Baseline candidate

| Setting/observation | Value |
| --- | --- |
| Chunker | Sequential whole-caption word windows |
| Target words | 200 |
| Overlap words | 35 |
| Maximum words | 300 |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Retrieval `k` | 5 |
| Existing baseline chunk count | 725 |
| Existing chunk average | 203.4 words |
| Existing chunk maximum | 210 words |

These are preprocessing observations and candidate reference settings, not
retrieval evaluation results or evidence of an optimal configuration. The
embedding model and `k` are recorded from the experimentation brief as the
candidate baseline; they are not independently confirmed by the persisted
index files. Record actual loaded model, retrieval settings, dependency
versions, and timestamp at each measured run.

## Workspace and output policy

See [`../README.md`](../README.md) for the directory layout. Keep notebooks,
experiment-only helpers, versioned evaluation data, and concise reviewed notes
in this workspace. Keep indexes, caches, and generated run outputs in ignored
local paths. Save only deliberately selected portable result files for review.
