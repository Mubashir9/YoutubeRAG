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

An OpenAI key is optional at this stage. Without one, the application explicitly remains retrieval-only. The supplied `transcript.json` remains unchanged; Phase 2 will validate it and create canonical processed data.

