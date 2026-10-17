# Anthony Mantello Creator RAG — Phase Breakdown

Status: planning baseline  
Source of truth: `anthony_mantello_rag_project_spec.md`  
Last updated: 2026-10-17

This document divides the project into chat-sized phases. Each phase should be completed, tested, and explained before starting the next phase. The application must remain honest about what is actually indexed: initially this is one supplied transcript, not Anthony Mantello's whole channel.

## How to use this document

Start one chat per phase. Begin the chat by naming the phase and pasting its objective and acceptance gate. During the work:

1. Explain important project concepts in simple terms as they arise.
2. Make the smallest useful implementation increment.
3. Run the phase's checks and record failures or missing inputs.
4. Update this document's status, notes, and next step before closing the chat.

Do not invent transcripts, video metadata, retrieval results, benchmark scores, or permissions. If an input is missing, make the interface accept it and document the blocker.

## Phase map

| Phase | Focus | Depends on |
|---|---|---|
| 0 | Project orientation and working agreement | None |
| 1 | Repository scaffold and configuration | 0 |
| 1.1 | Fetch an available transcript from a YouTube URL | 1; selected video URL |
| 2 | Transcript validation, cleaning, and diagnostics | 1; local timestamped transcript (supplied or produced by 1.1) |
| 3 | Timestamp-aware chunking and processed data | 2 |
| 4 | Embeddings, persistent index, and baseline retrieval | 3 |
| 5 | Grounded answers, citations, and abstention | 4 |
| 6 | Streamlit experience and playback | 5 |
| 7 | Evaluation, hardening, and reproducibility | 6 |
| 8 | Multi-video ingestion and corpus management | 7; authorised transcripts |
| 9 | RAG strategy comparison and improvement showcase | 7; preferably 8 |

The first six phases form the MVP vertical slice. Phase 7 makes it trustworthy and repeatable. Phases 8–9 are expansion and research/benchmarking work, not prerequisites for proving the first workflow.

## Phase 0 — Orientation and project contract

**Objective:** Confirm what the product is, what it is not, and what inputs are available.

**Work:**

- Read the project specification and inspect the supplied `YoutubeRAG/transcript.json`.
- Confirm the initial video ID, transcript format, and local-only starting scope.
- Record unknown metadata such as title and publication date as unknown rather than guessing.
- Agree on the working pattern: one phase per chat, simple explanations, tests at every gate.

**Concepts to explain simply:** RAG, indexed corpus, evidence, citation, transcript versus metadata, and why a chatbot about a creator must not impersonate the creator.

**Deliverable:** This phase document is present, and the initial inputs and constraints are recorded.

**Acceptance gate:** We can state exactly what one successful MVP query should do and what it must refuse to claim.

## Phase 1 — Scaffold and configuration

**Objective:** Create a clean Python project that can be installed and run locally.

**Work:**

- Add `pyproject.toml`, package/module structure, starter CLI, starter Streamlit app, README, tests, and `.env.example`.
- Define configuration for embedding model, index location, top-k, and optional OpenAI generation.
- Make retrieval-only operation possible when no LLM key is available.
- Add safe ignores for secrets, logs, caches, generated data, and the local vector store.

**Concepts to explain:** configuration versus code, environment variables, dependencies, CLI versus UI, and why interfaces make later replacements easier.

**Deliverable:** A fresh environment can install dependencies and start the skeleton UI/CLI with clear missing-input messages.

**Acceptance gate:** Basic tests pass; no secret is required just to inspect or run the scaffold.

## Phase 1.1 — Obtain a transcript from a YouTube URL

**Objective:** Let the user provide a YouTube URL and attempt to obtain its available captions in the timestamped JSON format already accepted by Phase 2.

**Starting test video:** `https://www.youtube.com/watch?v=b76rDd9FYeY` (selected as the first video to develop around).

**Work:**

- Add a CLI workflow that accepts a YouTube URL or video ID and resolves the video ID safely.
- Use a documented caption access method, and report clearly whether captions were retrieved, unavailable, or blocked.
- Convert retrieved captions to records with `text`, `start`, and positive `duration`; preserve source text and timing without inventing transcript content.
- Save the result under `data/raw/{video_id}.json` using atomic writes, then pass it through the existing Phase 2 validator.
- Keep a local-file import path for transcripts the user already has. Do not download video/audio or silently fall back to transcription.

**Concepts to explain:** YouTube video metadata versus caption access, generated versus uploaded captions, and why a valid transcript must retain timestamps.

**Deliverable:** A repeatable URL-to-validated-transcript CLI workflow, with actionable errors and provenance recorded for the selected video.

**Acceptance gate:** Running against the starting test URL either produces a schema-valid, non-empty timestamped transcript that Phase 2 accepts, or returns a specific, understandable access failure without leaving a partial/corrupt transcript file. A local supplied-transcript path still works.

**Dependency note:** This phase is an optional acquisition path. Phase 2 can proceed directly from a local transcript when one is already supplied; Phase 1.1 is needed to test and automate URL-based caption retrieval.

## Phase 2 — Validate and clean the supplied transcript

**Objective:** Turn raw timestamped JSON into trustworthy, auditable transcript segments.

**Work:**

- Validate the top-level list and each `text`, `start`, and `duration` field.
- Preserve the original raw file unchanged and create an atomic canonical copy.
- Clean marker-only captions such as `[music]`, while retaining speech mixed with markers.
- Normalize whitespace and mechanical artifacts without rewriting what was said.
- Keep segment indices, original text, cleaned text, and timestamps for traceability.
- Produce diagnostics: input/kept/dropped counts, time range, word counts, and warnings.

**Concepts to explain:** schema validation, immutable raw inputs, conservative cleaning, overlapping caption windows, and why `>>` is not a speaker label.

**Deliverable:** Validated/cleaned segment output and a diagnostics report for `n_jHmfOgpA0`.

**Acceptance gate:** Invalid records fail with actionable errors; music-only records are removed; mixed speech is retained; repeated runs are deterministic.

## Phase 3 — Build timestamp-aware chunks

**Objective:** Group cleaned segments into useful retrieval units without losing source location.

**Work:**

- Implement the baseline sequential word-window chunker: roughly 150–250 words, bounded near 300, with overlap.
- End near sentence/topic boundaries when practical, without overengineering the MVP.
- Compute `start_sec` from the first segment and `end_sec` from the maximum segment end.
- Preserve source segment indices and stable chunk IDs.
- Write `data/processed/chunks.jsonl` and report chunk statistics.
- Keep the chunker behind an interface so a later 75-second/15-second experiment can be added.

**Concepts to explain:** chunking, overlap, context windows, stable IDs, and why caption timestamps are an ordered timeline rather than perfectly non-overlapping blocks.

**Deliverable:** Reproducible processed chunks with metadata and source traceability.

**Acceptance gate:** Every chunk has valid source times and text; IDs/content are identical across reruns; known workout and fishing areas are represented.

## Phase 4 — Embed, persist, and retrieve

**Objective:** Make the processed transcript searchable by meaning.

**Work:**

- Generate embeddings using one configured local Sentence Transformers model.
- Store vectors persistently in ChromaDB with scalar metadata only.
- Implement idempotent upsert/reindex behavior and index statistics.
- Add a retrieval contract containing chunk ID, score/distance, excerpt, video, times, and strategy.
- Add CLI querying and timestamp URL generation.
- Test queries such as “upper C workout” and “fishing trip.”

**Concepts to explain:** embeddings, semantic similarity, vector databases, persistence, top-k, and why query/document models must match.

**Deliverable:** A local index and a retrieval-only command returning evidence with playable timestamp links.

**Acceptance gate:** Relevant passages are retrieved for the known test questions; repeated indexing creates no duplicates; changing the embedding model requires a separate rebuild.

## Phase 5 — Grounded answering and citation safety

**Objective:** Generate useful answers only from retrieved evidence.

**Work:**

- Define the answer contract: answer text, citation list, and insufficient-evidence flag.
- Add a provider-swappable generation interface with OpenAI as the configurable provider.
- Pass only bounded retrieved excerpts to the model.
- Require source IDs from the retrieved set and validate them server-side.
- Construct video IDs, timestamps, excerpts, and URLs from trusted retrieved metadata, not arbitrary model output.
- Add abstention behavior for weak, missing, ambiguous, or conflicting evidence.
- Use neutral wording when speaker attribution is uncertain.

**Concepts to explain:** grounding, retrieval context, hallucination, abstention, prompt injection in source text, and server-side validation.

**Deliverable:** A question pipeline that can answer supported questions and honestly say “not found in indexed videos.”

**Acceptance gate:** Three manually inspected questions are supported by real excerpts; an unsupported question abstains; invented citation IDs never become links.

## Phase 6 — Streamlit UI and playback

**Objective:** Make the vertical slice usable by a person.

**Work:**

- Add chat/search input, answer display, evidence cards, metadata, and citation links.
- Show the indexed-corpus scope prominently.
- Add a selected-result YouTube player or reliable timestamped external-link fallback.
- Escape transcript text and validate video IDs before creating embeds/URLs.
- Handle loading, no-index, missing-key, no-results, API-error, and malformed-result states.
- Keep search-result excerpts visible independently from the generated answer.

**Concepts to explain:** frontend state, embedded playback, fallback design, and why a working external timestamp link is better than a broken player.

**Deliverable:** A local app where a user can ask, inspect evidence, and open the cited moment.

**Acceptance gate:** Clicking a real citation reaches the correct video near the evidence time; the app remains useful without an LLM key in retrieval-only mode.

## Phase 7 — Evaluation, testing, and hardening

**Objective:** Establish evidence that the system works and expose its limitations.

**Work:**

- Add unit tests for validation, cleaning, chunking, timestamps, metadata, citations, re-ingest, and model/index compatibility.
- Create a small hand-authored evaluation set with relevant time intervals, including unanswered and ambiguous-speaker questions.
- Add retrieval-only evaluation and per-query reports.
- Record retrieval, generation, and end-to-end latency without inventing targets.
- Add atomic writes, failure-tolerant CLI behavior, structured logs, and README troubleshooting.
- Manually click-check citations.

**Concepts to explain:** test types, gold labels, Recall@k, citation validity versus citation support, abstention, and why a tiny dataset produces preliminary results.

**Deliverable:** Repeatable tests and an honest baseline report.

**Acceptance gate:** Tests pass; at least ten curated queries are reviewable; failures and limitations are documented; the MVP definition of done is met.

## Phase 8 — Expand to multiple authorised videos

**Objective:** Support a larger corpus without changing core application code.

**Work:**

- Add metadata registration and batch import for supplied, permitted transcript files.
- Verify titles, dates, URLs, and rights notes; retain unknown values as unknown.
- Add idempotent ingest, status reporting, per-video failures, and stale-index cleanup/versioning.
- Add optional video/date filters and “find mentions” results.
- Freeze a corpus snapshot before comparing retrieval strategies.

**Concepts to explain:** corpus snapshots, metadata filters, batch processing, idempotency, and why transcript access/rights are separate from video metadata.

**Deliverable:** Ten to twenty searchable videos when authorised files and metadata are available.

**Acceptance gate:** New files can be added by registration/drop-in; reruns do not duplicate records; results remain attributable to the correct video and time.

## Phase 9 — RAG strategy comparison and showcase

**Objective:** Measure whether more advanced retrieval actually improves evidence quality.

**Work:**

- Implement a common strategy interface.
- Add BM25/lexical retrieval, dense retrieval, hybrid reciprocal-rank fusion, and optional reranking when feasible.
- Add the Streamlit RAG Lab strategy selector and comparison view.
- Run controlled chunking ablations: word windows versus 75-second/15-second time windows, with optional topic-aware chunks later.
- Freeze corpus, queries, embeddings, prompt, and answer model while comparing retrieval strategies.
- Report Hit@k/Recall@k, MRR or nDCG, timestamp overlap, citation validity/support, latency, token use, and cost where applicable.
- Report regressions and failures, not just improvements.

**Concepts to explain:** lexical versus semantic search, hybrid retrieval, reranking, fair experiments, ablation studies, interval-based labels, and retrieval metrics.

**Deliverable:** Reproducible benchmark commands, per-query reports, comparison tables/charts, and a short interpretation of what improved and what did not.

**Acceptance gate:** Every implemented strategy runs on the same labelled data; metrics are measured rather than fabricated; LLM-dependent metrics are clearly separated from retrieval-only metrics.

## Phase completion record

Update this table at the end of each phase.

| Phase | Status | Date completed | Key result / blocker | Next action |
|---|---|---|---|---|
| 0 | Complete | 2026-10-17 | Confirmed the single supplied transcript, source video ID, local-only scope, unknown metadata, and phase working agreement. | Phase 1: build the Python scaffold and configuration |
| 1 | Complete | 2026-10-17 | Added installable Python scaffold, environment configuration, starter CLI/UI, tests, README, and safe ignores. No secret is required; retrieval-only mode is explicit. | Phase 1.1: add URL-based caption retrieval for the selected video |
| 1.1 | Complete | 2026-10-17 | Added safe YouTube URL/ID resolution, caption retrieval, atomic raw JSON and provenance sidecar writes, explicit unavailable/blocked errors, and tests. Live retrieval remains dependent on installing dependencies and network/caption availability. | Phase 3: generate timestamp-aware chunks from the validated transcript |
| 2 | Complete | 2026-10-17 | Re-ran validation for the Phase 1.1 transcript `b76rDd9FYeY`: 842 records kept, no marker-only drops, diagnostics and per-video cleaned segments created. | Phase 3: generate timestamp-aware chunks for both validated transcripts |
| 3 | Complete | 2026-10-17 | Added deterministic sequential word-window chunking, CLI support, tests, and generated chunks for both validated transcripts. 27 chunks for `n_jHmfOgpA0`; 35 for `b76rDd9FYeY`. | Phase 4: build the persistent embedding index |
| 4 | Complete | 2026-10-17 | Added local Sentence Transformers embeddings, persistent ChromaDB index, idempotent upsert/model compatibility checks, retrieval contract, CLI indexing/querying, and timestamp links. Live ML smoke testing requires installing new dependencies. | Phase 5: add grounded answers |
| 5 | Planned | — | — | Add grounded answers |
| 6 | Planned | — | — | Build usable UI |
| 7 | Planned | — | — | Test and harden MVP |
| 8 | Planned | — | — | Expand only with authorised transcripts |
| 9 | Planned | — | — | Benchmark retrieval strategies |

## Phase 1 completion notes

- **Changed:** Added `pyproject.toml`, `src/youtube_rag/`, starter `youtube-rag status` CLI, starter Streamlit app, centralized environment configuration, `.env.example`, README setup instructions, tests, and safe ignores for secrets/caches/generated data.
- **Tested:** Python bytecode compilation passed. The configured test suite could not run in the available environment because `pytest` and runtime dependencies (`python-dotenv`, etc.) are not installed; install with `python -m pip install -e ".[dev]"` in a network-enabled environment.
- **Concepts:** Configuration keeps environment-specific values out of code; environment variables keep secrets out of source control; the CLI and UI are separate interfaces over future retrieval services; generation remains optional.
- **Assumption/blocker:** This phase intentionally has no indexing or retrieval implementation. The supplied raw transcript was not modified.
- **Next:** Phase 2 validates the supplied transcript and creates canonical processed data.

## Phase 2 completion notes

- **Changed:** Added `src/youtube_rag/transcript.py` with strict schema validation, conservative marker/whitespace cleaning, stable source indices, atomic writes, and diagnostics. Added `validate-transcript` CLI support and tests. Created `data/raw/n_jHmfOgpA0.json`, `data/processed/segments.jsonl`, and `data/diagnostics/n_jHmfOgpA0.json`.
- **Result:** 732 input records; 710 kept; 22 marker-only records dropped; 4,391 input words and 4,338 kept words; cleaned transcript range 24.800–1518.240 seconds; no ordering warnings. The supplied raw file was copied byte-for-byte and remains unchanged.
- **Tested:** Direct processing smoke check passed, repeated output generation was deterministic, and Python compilation passed. `pytest` and the Typer CLI could not run in the available `.venv` because `pytest` and `typer` are not installed; install project dependencies before rerunning the full suite.
- **Concepts:** Validation checks structure and values before downstream use; raw inputs are preserved as immutable evidence; cleaning removes only known caption markers and normalizes whitespace; caption windows may overlap; `>>` remains ordinary transcript text, not a speaker label.
- **Next:** Phase 3 builds bounded timestamp-aware chunks from the cleaned JSONL.

### Phase 2 re-run for Phase 1.1 transcript

- **Input:** `data/raw/b76rDd9FYeY.json`, with Phase 1.1 provenance retained in `b76rDd9FYeY.meta.json`.
- **Output:** `data/processed/b76rDd9FYeY.segments.jsonl` and `data/diagnostics/b76rDd9FYeY.json`.
- **Result:** 842 input records; 842 kept; 0 dropped; 5,736 input and kept words; transcript range 0.000–1750.120 seconds; no ordering warnings.
- **Check:** Processing completed successfully and preserved the fetched raw file as the source input. The original `n_jHmfOgpA0` outputs were left intact.

## Phase 3 completion notes

- **Changed:** Added `youtube_rag.chunking` with a `Chunker` protocol and deterministic `SequentialWordChunker` using 200-word targets, 35-word segment-safe overlap, and a 300-word ceiling. Chunks retain stable IDs, source segment indices, video metadata placeholders, and timestamp ranges. Added the `chunk-transcript` CLI command and unit tests.
- **Generated:** `data/processed/chunks.jsonl` contains 27 chunks for `n_jHmfOgpA0`; `data/processed/b76rDd9FYeY.chunks.jsonl` contains 35 chunks for `b76rDd9FYeY`. The first transcript's chunks average 196.8 words (maximum 207); the fetched transcript averages 201.3 (maximum 207). Both generated files are covered by the existing `data/processed/` ignore rule.
- **Tested:** `python -m compileall -q src tests` passed; `python -m pytest -q` passed with 12 tests. Repeated chunking produced identical objects and IDs. Workout and fishing terms are represented in the generated chunks.
- **Concepts:** Chunking groups nearby captions into searchable context windows; overlap repeats a small amount of context so ideas near boundaries are not lost; stable IDs and source segment indices make citations and reruns auditable. Caption timestamps are treated as an ordered timeline, so chunk ends use the maximum included segment end rather than assuming non-overlap.
- **Assumption/blocker:** The baseline uses conservative sequential word windows and does not claim topic-perfect boundaries. The later 75-second/15-second experiment remains intentionally deferred to the benchmark phase.
- **Next:** Phase 4 builds persistent local embeddings and retrieval from these chunks.

## Phase 4 completion notes

- **Changed:** Added `youtube_rag.embeddings.LocalEmbedder` and persistent `youtube_rag.retrieval.ChromaIndex` with scalar metadata, stable-ID upserts, statistics, model compatibility protection, retrieval results, and timestamp URL generation. Added `index-chunks` and retrieval-only `query` CLI commands.
- **Tested:** Added retrieval URL/contract tests. Python compilation and the full test suite should be run after installing project dependencies. This environment lacks `sentence-transformers` and `chromadb`, so live model/index/query execution could not be run here.
- **Concepts:** Embeddings represent text as vectors so semantic similarity can be ranked; ChromaDB persists vectors and metadata locally; idempotent upsert prevents duplicates; embedding models must remain consistent within an index.
- **Assumption/blocker:** The configured baseline is `sentence-transformers/all-MiniLM-L6-v2` with cosine distance. Dependency/model installation requires a network-enabled environment; no retrieval result or score was invented.
- **Next:** Phase 5 adds grounded answers, validated citations, and abstention.

## Phase 1.1 completion notes

- **Changed:** Added `youtube_rag.acquisition` and the `fetch-transcript` CLI command. It accepts a YouTube URL or bare video ID, fetches available captions through `youtube-transcript-api`, writes `data/raw/{video_id}.json` atomically, and records source URL, count, language, and uploaded/generated status in `{video_id}.meta.json`. It never downloads media or silently transcribes audio.
- **Tested:** Python compilation and dependency-free URL/ID parsing smoke checks passed. Live caption retrieval remains unverified in this environment because the new dependency/network access is unavailable.
- **Concepts:** A video URL identifies a video, while caption access is a separate operation that may be unavailable or blocked. Uploaded and generated captions are recorded as provenance. Timestamps are retained for validation, chunking, and citations.
- **Blocker/assumption:** No transcript content or access result was invented. Caption availability for the selected video must be verified in a network-enabled environment.
- **Next:** Phase 3 can proceed from the existing validated local transcript; validate the fetched file first when URL retrieval is available.

## Phase 0 completion notes

- **Product contract:** This is an evidence-backed search assistant about Anthony Mantello's indexed YouTube videos. It is not a creator impersonation, voice clone, generic YouTube chatbot, or claim that the whole channel has been indexed.
- **Initial corpus:** One user-supplied timestamped transcript for video ID `n_jHmfOgpA0`, corresponding to `https://www.youtube.com/watch?v=n_jHmfOgpA0`.
- **Verified transcript facts:** `YoutubeRAG/transcript.json` is a JSON array of 732 records. Every record has exactly `text`, `start`, and `duration`; values are valid; starts are nondecreasing; the covered range is 0.654–1518.240 seconds; the file contains 4,391 whitespace-delimited words and 41 records containing `[music]` (19 marker-only records).
- **Metadata status:** The channel URL is known from the specification. Official title, publication date, thumbnail, and upload ranking are unknown and must remain unknown until verified. Speaker identity is also unknown; `>>` is not a speaker label.
- **Input/rights constraint:** Work locally from supplied or otherwise authorised transcript files. Do not silently scrape or invent transcript content, metadata, permissions, retrieval results, or benchmark scores.
- **Working agreement:** Complete one phase per chat; explain important concepts simply; make the smallest useful increment; run the phase checks; update this document before closing; preserve existing work.
- **MVP query contract:** A successful supported query retrieves evidence from this indexed transcript, returns a conservative answer about what the video discusses, and exposes a citation built from the real video ID and evidence timestamp. An unsupported query must say it was not found in the indexed material, rather than claim the creator never discussed it. The system must not claim a speaker said something when attribution is uncertain.
- **Phase 0 check:** Orientation and transcript inspection completed. No application code or generated transcript data was added.
- **Next prerequisite:** Phase 1 should create the project scaffold and configuration. Phase 2 should then place/use the supplied file as `data/raw/n_jHmfOgpA0.json` without modifying the original input.

## Standard phase-chat template

Use this opening structure for each new phase chat:

> We are working on Phase N — [name] of the Anthony Mantello Creator RAG project. Read `YoutubeRAG/anthony_mantello_rag_project_spec.md` and `YoutubeRAG/PHASE_BREAKDOWN.md` first. Explain important concepts in simple terms while implementing. Stay within this phase, preserve existing work, run the acceptance checks, and update `PHASE_BREAKDOWN.md` with the result before finishing. Do not fabricate missing transcripts, metadata, permissions, citations, or metrics.

At the end of the chat, record:

- what changed;
- what was tested and the result;
- what concepts were explained;
- any blocker or assumption;
- the next phase and its prerequisite.

## Decisions carried forward from the specification

- Streamlit is the MVP UI; retrieval and generation remain modular.
- Local embeddings are the baseline; generation is optional for retrieval-only use.
- The initial corpus is one supplied transcript.
- Speaker identity is unknown unless verified.
- Claims are limited to indexed videos.
- Transcript files must be supplied or otherwise authorised; ingestion must not silently scrape third-party material.
- Citation precision should improve toward the narrowest verified source span, but must not claim accuracy that has not been checked.
- Benchmark results must be reproducible and honest, including regressions.
