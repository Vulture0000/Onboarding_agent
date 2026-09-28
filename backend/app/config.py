"""Application configuration loaded from environment variables."""
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    gemini_embedding_model: str = os.getenv(
        "GEMINI_EMBEDDING_MODEL", "models/text-embedding-004"
    )
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/onboarding.db")

    data_dir: Path = BACKEND_DIR / "data"
    policies_dir: Path = BACKEND_DIR / "data" / "policies"
    uploads_dir: Path = BACKEND_DIR / "data" / "uploads"
    faiss_index_dir: Path = BACKEND_DIR / "data" / "faiss_index"

    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
        ).split(",")
        if o.strip()
    ]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.uploads_dir.mkdir(parents=True, exist_ok=True)
    s.faiss_index_dir.mkdir(parents=True, exist_ok=True)
    return s


settings = get_settings()
