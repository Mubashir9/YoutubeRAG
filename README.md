# Youtube RAG

Generation uses `LLM_PROVIDER=groq` by default, or `LLM_PROVIDER=openai`.
Set `GROQ_API_KEY` and optionally `GROQ_MODEL` (default `openai/gpt-oss-20b`).
Without the selected key, the CLI and Streamlit app remain in retrieval-only mode.
Keep keys in `.env` and never commit them.
