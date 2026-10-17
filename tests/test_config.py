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

def test_groq_is_default_generation_provider(monkeypatch):
    for key in ("LLM_PROVIDER", "GROQ_API_KEY", "GROQ_MODEL"): monkeypatch.delenv(key, raising=False)
    s = Settings.from_env(env_file=None)
    assert s.llm_provider == "groq"
    assert s.groq_model == "openai/gpt-oss-20b"

def test_provider_and_model_are_configurable(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    s = Settings.from_env(env_file=None)
    assert (s.llm_provider, s.groq_model) == ("openai", "openai/gpt-oss-120b")

def test_unknown_provider_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "local")
    with pytest.raises(ValueError, match="LLM_PROVIDER"): Settings.from_env(env_file=None)

