"""Application configuration.

The original project assumed it would always be started from the project
directory and that every external API key was present.  That is convenient
for a first local prototype, but it makes health checks and deployment fail
before FastAPI can even start.  Configuration is now optional and all paths
are anchored to the project root unless explicitly overridden.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

try:
    from google import genai
except ImportError:  # pragma: no cover - handled by the deployment install
    genai = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _path_env(name: str, default: str) -> str:
    raw_value = os.getenv(name, default).strip()
    path = Path(raw_value)
    return str(path if path.is_absolute() else PROJECT_ROOT / path)


# API keys are intentionally optional.  The app can still serve the UI,
# health endpoint, memory features, calculator, date, and order tools when a
# provider is not configured.
GEMINI_API_KEY = _optional_env("GEMINI_API_KEY")
OPENWEATHER_API_KEY = _optional_env("OPENWEATHER_API_KEY")
TAVILY_API_KEY = _optional_env("TAVILY_API_KEY")


client = None
if GEMINI_API_KEY and genai is not None:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        # A malformed or unavailable provider configuration should not take
        # down the UI, health endpoint, or local tools.
        client = None


CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")

DB_PATH = _path_env("DB_PATH", "conversations.db")
CHROMA_PATH = _path_env("CHROMA_PATH", "chroma_store")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "knowledge_base")

_cors_value = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [origin.strip() for origin in _cors_value.split(",") if origin.strip()]
if not CORS_ORIGINS:
    CORS_ORIGINS = ["*"]

STATIC_PATH = PROJECT_ROOT / "static"
DOCUMENTS_PATH = PROJECT_ROOT / "data" / "docs"
