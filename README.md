# Anthony Mantello Creator RAG

Local, evidence-backed search over transcript files supplied or authorised by the user. The initial corpus is one transcript for video `n_jHmfOgpA0`; this project does not claim to index the creator's whole channel or impersonate the creator.

## Phase 1 scaffold

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
youtube-rag status
streamlit run src/youtube_rag/streamlit_app.py
pytest
```

## Phase 4: local semantic retrieval

```powershell
python -m pip install -e ".[dev]"
youtube-rag index-chunks --chunks data/processed/chunks.jsonl
youtube-rag query "upper C workout"
youtube-rag query "fishing trip"
```

The persistent index defaults to `data/index` and upserts by stable chunk ID, so reruns do not create duplicates. Retrieval works without an OpenAI key and returns distances, excerpts, source times, and timestamp URLs.

An OpenAI key is optional at this stage. Without one, the application explicitly remains retrieval-only. The supplied `transcript.json` remains unchanged; Phase 2 will validate it and create canonical processed data.

