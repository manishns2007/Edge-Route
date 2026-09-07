"""
EdgeRoute Configuration
=======================
All settings loaded from environment variables (.env).
Never hard-code secrets here.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file when inside edgeroute/)
_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
else:
    # Also try same-directory .env (when running from edgeroute/)
    load_dotenv()


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value.strip())
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Ollama / SLM
# ---------------------------------------------------------------------------
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

# Timeout in seconds for Ollama inference calls
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))

# ---------------------------------------------------------------------------
# Router / Policy
# ---------------------------------------------------------------------------
# Minimum SLM confidence to trust the SLM classification directly
SLM_CONFIDENCE_THRESHOLD: float = _float(
    os.getenv("SLM_CONFIDENCE_THRESHOLD"), 0.70
)

# Complexity signal threshold above which a request is considered CLOUD_COMPLEX
COMPLEXITY_THRESHOLD: float = _float(
    os.getenv("COMPLEXITY_THRESHOLD"), 0.70
)

# Word count above which a request is *probably* complex regardless of SLM
COMPLEXITY_WORD_THRESHOLD: int = int(os.getenv("COMPLEXITY_WORD_THRESHOLD", "60"))

# ---------------------------------------------------------------------------
# Cloud Adapter
# ---------------------------------------------------------------------------
MOCK_CLOUD: bool = _bool(os.getenv("MOCK_CLOUD"), True)
CLOUD_API_KEY: str = os.getenv("CLOUD_API_KEY", "")
CLOUD_MODEL: str = os.getenv("CLOUD_MODEL", "gpt-4o-mini")
CLOUD_API_BASE: str = os.getenv("CLOUD_API_BASE", "https://api.openai.com/v1")

# ---------------------------------------------------------------------------
# Dry-run mode: skips live SLM generation for non-routing steps
# ---------------------------------------------------------------------------
DRY_RUN: bool = _bool(os.getenv("DRY_RUN"), False)

# ---------------------------------------------------------------------------
# API server
# ---------------------------------------------------------------------------
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# ---------------------------------------------------------------------------
# Logging / Debug
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
DEBUG: bool = _bool(os.getenv("DEBUG"), False)

# ---------------------------------------------------------------------------
# Valid route labels (single source of truth)
# ---------------------------------------------------------------------------
VALID_ROUTES = {"LOCAL_SIMPLE", "LOCAL_COMMAND", "CLOUD_COMPLEX", "AMBIGUOUS"}

# Ordered list of allowed local tools (allowlist — never trust arbitrary names)
ALLOWED_TOOLS = [
    "turn_on_light",
    "turn_off_light",
    "set_temperature",
    "start_music",
    "lock_door",
]
