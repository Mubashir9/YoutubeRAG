"""Central configuration loaded from environment variables."""
from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    index_dir: Path = Path("data/index")
    top_k: int = 5
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    llm_provider: str = "groq"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    @classmethod
    def from_env(cls, env_file: str | Path | None = ".env") -> "Settings":
        if env_file: load_dotenv(env_file)
        top_k = int(os.getenv("TOP_K", "5"))
        if top_k < 1: raise ValueError("TOP_K must be at least 1")
        provider = os.getenv("LLM_PROVIDER", cls.llm_provider).strip().lower()
        if provider not in {"groq", "openai"}:
            raise ValueError("LLM_PROVIDER must be 'groq' or 'openai'")
        return cls(
            os.getenv("EMBEDDING_MODEL", cls.embedding_model),
            Path(os.getenv("INDEX_DIR", str(cls.index_dir))), top_k,
            os.getenv("OPENAI_API_KEY") or None,
            os.getenv("OPENAI_MODEL", cls.openai_model), provider,
            os.getenv("GROQ_API_KEY") or None,
            os.getenv("GROQ_MODEL", cls.groq_model),
        )

