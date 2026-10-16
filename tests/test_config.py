from pathlib import Path
import pytest
from youtube_rag.config import Settings
def test_defaults_are_retrieval_only(monkeypatch):
    for key in ("EMBEDDING_MODEL", "INDEX_DIR", "TOP_K", "OPENAI_API_KEY", "OPENAI_MODEL"): monkeypatch.delenv(key, raising=False)
    s = Settings.from_env(env_file=None)
    assert s.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert s.index_dir == Path("data/index")
    assert s.top_k == 5
    assert s.openai_api_key is None
def test_top_k_must_be_positive(monkeypatch):
    monkeypatch.setenv("TOP_K", "0")
    with pytest.raises(ValueError, match="TOP_K"): Settings.from_env(env_file=None)

