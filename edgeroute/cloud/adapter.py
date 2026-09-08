"""
cloud/adapter.py
================
Optional cloud LLM adapter.

IMPORTANT ARCHITECTURAL RULE:
  - This module is NEVER called during local classification.
  - It is only invoked AFTER the local policy engine has decided the route
    is CLOUD_COMPLEX.
  - Classification always happens locally, regardless of this module.

When MOCK_CLOUD=true (the default), a deterministic mock response is returned
so the application can run end-to-end without any external API credentials.

When MOCK_CLOUD=false, a real cloud API is called using the configured
CLOUD_API_KEY and CLOUD_API_BASE.  The default implementation targets
OpenAI-compatible APIs.  The API key must be set via the CLOUD_API_KEY
environment variable — never hard-coded.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    CLOUD_API_BASE,
    CLOUD_API_KEY,
    CLOUD_MODEL,
    MOCK_CLOUD,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CloudResponse:
    """Response from the cloud LLM adapter."""
    text: str = ""
    model: str = ""
    mock: bool = False
    error: str = ""
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Mock response generator
# ---------------------------------------------------------------------------

_MOCK_TEMPLATE = """\
[MOCK CLOUD RESPONSE — EdgeRoute Demo Mode]

This response simulates what a large cloud language model would return
for the following request:

"{query}"

In production (with MOCK_CLOUD=false and a valid CLOUD_API_KEY), this
would be replaced by an actual response from {model}.

To enable live cloud inference:
  1. Set MOCK_CLOUD=false in your .env file.
  2. Set CLOUD_API_KEY=<your-api-key>.
  3. Optionally set CLOUD_API_BASE and CLOUD_MODEL.

Note: The routing/classification decision was made entirely locally by
EdgeRoute before this cloud adapter was invoked.
"""


def _mock_response(query: str) -> CloudResponse:
    return CloudResponse(
        text=_MOCK_TEMPLATE.format(query=query[:200], model=CLOUD_MODEL),
        model=f"mock/{CLOUD_MODEL}",
        mock=True,
        latency_ms=0.0,
    )


# ---------------------------------------------------------------------------
# Live cloud call (OpenAI-compatible)
# ---------------------------------------------------------------------------

def _live_response(query: str) -> CloudResponse:
    """
    Call an OpenAI-compatible API.

    Never hard-codes the API key; reads from CLOUD_API_KEY env variable.
    """
    if not CLOUD_API_KEY:
        logger.warning("CLOUD_API_KEY not set; falling back to mock response.")
        return _mock_response(query)

    try:
        import httpx

        t0 = time.perf_counter()
        headers = {
            "Authorization": f"Bearer {CLOUD_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": CLOUD_MODEL,
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 1024,
        }
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{CLOUD_API_BASE}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            latency_ms = (time.perf_counter() - t0) * 1000
            return CloudResponse(
                text=text,
                model=CLOUD_MODEL,
                mock=False,
                latency_ms=latency_ms,
            )
    except Exception as exc:  # noqa: BLE001
        logger.error("Cloud API call failed: %s", exc)
        return CloudResponse(
            text="[Cloud LLM unavailable — API call failed]",
            model=CLOUD_MODEL,
            mock=False,
            error=str(exc),
            latency_ms=0.0,
        )


# ---------------------------------------------------------------------------
# Main adapter class
# ---------------------------------------------------------------------------

class CloudLLMAdapter:
    """
    Adapter over an optional cloud LLM.

    Classification NEVER goes through this adapter.
    This is only called after the local routing decision is final.
    """

    def __init__(
        self,
        mock: bool | None = None,
        api_key: str | None = None,
    ) -> None:
        self.use_mock = mock if mock is not None else MOCK_CLOUD
        self._api_key = api_key or CLOUD_API_KEY

    def generate(self, query: str) -> CloudResponse:
        """
        Generate a cloud LLM response for a query that has already been
        classified as CLOUD_COMPLEX by the local router.

        Returns CloudResponse — never raises.
        """
        t0 = time.perf_counter()
        try:
            if self.use_mock:
                logger.info("Cloud adapter: MOCK_CLOUD=true — returning mock response.")
                resp = _mock_response(query)
            else:
                logger.info("Cloud adapter: sending request to %s / %s", CLOUD_API_BASE, CLOUD_MODEL)
                resp = _live_response(query)
            resp.latency_ms = (time.perf_counter() - t0) * 1000
            return resp
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error in cloud adapter: %s", exc)
            return CloudResponse(
                text="[Cloud adapter error]",
                error=str(exc),
                mock=self.use_mock,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

    @property
    def is_mock(self) -> bool:
        return self.use_mock
