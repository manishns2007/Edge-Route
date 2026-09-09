"""
models/slm.py
=============
LocalSLM — Abstraction over the Ollama-hosted Qwen2.5-0.5B-Instruct (or any
other compatible model).

Provides two operations:
  classify(query)  → structured JSON routing decision
  generate(query)  → free-form text response

Error handling is strict: the application must NEVER crash due to Ollama
being unavailable, slow, or returning malformed output.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

import ollama

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    VALID_ROUTES,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model for classification output
# ---------------------------------------------------------------------------

@dataclass
class SLMClassification:
    """Structured result produced by LocalSLM.classify()."""
    route: str = "AMBIGUOUS"
    confidence: float = 0.0
    reason: str = ""
    intent: str = ""
    raw_output: str = ""
    error: str = ""
    latency_ms: float = 0.0
    model_available: bool = True

    @property
    def is_valid(self) -> bool:
        return self.route in VALID_ROUTES and not self.error

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.70


@dataclass
class SLMResponse:
    """Free-form text response from LocalSLM.generate()."""
    text: str = ""
    error: str = ""
    latency_ms: float = 0.0
    model_available: bool = True


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)
_BARE_JSON_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _extract_json(text: str) -> dict[str, Any] | None:
    """
    Try to extract a JSON object from an arbitrary string.
    Handles:
      - Raw JSON
      - JSON wrapped in markdown fences
      - JSON surrounded by extra text
      - Nested-brace objects (first try full, then fallback to regex)
    """
    if not text:
        return None

    # 1. Try entire string first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. Try JSON inside markdown fences
    m = _JSON_FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Find the largest balanced {...} block
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    # 4. Regex fallback for simple single-level objects
    m = _BARE_JSON_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _normalise_route(route: str | None) -> str:
    """Map various model outputs to a canonical route label."""
    if not route:
        return "AMBIGUOUS"
    r = route.upper().strip()
    mapping = {
        "LOCAL_SIMPLE": "LOCAL_SIMPLE",
        "LOCAL SIMPLE": "LOCAL_SIMPLE",
        "SIMPLE": "LOCAL_SIMPLE",
        "LOCAL_COMMAND": "LOCAL_COMMAND",
        "LOCAL COMMAND": "LOCAL_COMMAND",
        "COMMAND": "LOCAL_COMMAND",
        "CLOUD_COMPLEX": "CLOUD_COMPLEX",
        "CLOUD COMPLEX": "CLOUD_COMPLEX",
        "COMPLEX": "CLOUD_COMPLEX",
        "CLOUD": "CLOUD_COMPLEX",
        "AMBIGUOUS": "AMBIGUOUS",
    }
    return mapping.get(r, "AMBIGUOUS")


def _parse_classification(raw: str) -> SLMClassification:
    """Parse SLM text output into a SLMClassification, never raises."""
    data = _extract_json(raw)
    if data is None:
        return SLMClassification(
            route="AMBIGUOUS",
            confidence=0.0,
            reason="Could not extract JSON from model output",
            raw_output=raw,
            error="json_parse_failure",
        )

    # Coerce confidence
    conf_raw = data.get("confidence", 0.0)
    try:
        confidence = float(conf_raw)
        # Handle percentage form (e.g. 95 instead of 0.95)
        if confidence > 1.0:
            confidence = confidence / 100.0
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    route = _normalise_route(data.get("route") or data.get("category") or "")

    return SLMClassification(
        route=route,
        confidence=confidence,
        reason=str(data.get("reason", "")),
        intent=str(data.get("intent", "")),
        raw_output=raw,
    )


# ---------------------------------------------------------------------------
# System prompt for classification
# ---------------------------------------------------------------------------

_CLASSIFICATION_SYSTEM_PROMPT = """\
You are an AI request router. Your ONLY job is to classify user requests into routing categories.

You MUST respond with ONLY a valid JSON object — no other text.

Routing categories:
- LOCAL_SIMPLE: Short factual questions, arithmetic, math calculations, definitions, simple lookups, unit conversions.
- LOCAL_COMMAND: Commands or requests to control/execute something on a device or tool (turn on/off light, set temperature, lock/unlock door, play music).
- CLOUD_COMPLEX: Long-form generation (>500 words), complex reasoning, creative writing, sophisticated coding, multi-step analysis, system design.
- AMBIGUOUS: Unclear, vague, or underspecified requests.

Response format (JSON only):
{
  "intent": "<one short sentence describing what the user wants>",
  "route": "<LOCAL_SIMPLE | LOCAL_COMMAND | CLOUD_COMPLEX | AMBIGUOUS>",
  "confidence": <float between 0.0 and 1.0>,
  "reason": "<one short sentence explaining the routing decision>"
}

Rules:
- Math, arithmetic, and calculations (e.g. "What is 200 + 0", "2 + 2", "15 * 4", "calculate 100 / 5") MUST be classified as LOCAL_SIMPLE, NEVER LOCAL_COMMAND.
- Questions asking for facts, definitions, or information (starting with What, Who, Where, How, Define) MUST be classified as LOCAL_SIMPLE.
- LOCAL_COMMAND is ONLY for controlling devices, appliances, or hardware tools (lights, thermostats, doors, music).
- If the request requires generating very long content, deep reasoning, or complex coding, use CLOUD_COMPLEX.
- If unsure or underspecified, use AMBIGUOUS.
- NEVER include anything outside the JSON object.
"""


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class LocalSLM:
    """
    Abstraction over a locally-hosted small language model via Ollama.

    The model name is read from config and can be changed through the
    OLLAMA_MODEL environment variable.
    """

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.host = host or OLLAMA_HOST
        self.model = model or OLLAMA_MODEL
        self.timeout = timeout or OLLAMA_TIMEOUT
        self._client = ollama.Client(host=self.host)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, query: str) -> SLMClassification:
        """
        Classify a user request into a routing category.
        Returns SLMClassification — never raises.
        """
        t0 = time.perf_counter()
        try:
            response = self._client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": _CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Classify this request: {query}"},
                ],
                options={"temperature": 0.1, "num_predict": 200},
            )
            raw = response.message.content or ""
            latency_ms = (time.perf_counter() - t0) * 1000
            result = _parse_classification(raw)
            result.latency_ms = latency_ms
            result.model_available = True
            logger.debug(
                "classify(%r) → route=%s conf=%.2f latency=%.0fms",
                query[:60],
                result.route,
                result.confidence,
                latency_ms,
            )
            return result

        except ollama.ResponseError as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            error_msg = str(exc)
            logger.warning("Ollama ResponseError during classify: %s", error_msg)
            return SLMClassification(
                error=f"model_error: {error_msg}",
                latency_ms=latency_ms,
                model_available=True,
            )

        except ConnectionError as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.warning("Ollama not reachable: %s", exc)
            return SLMClassification(
                error="ollama_unavailable",
                latency_ms=latency_ms,
                model_available=False,
            )

        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.error("Unexpected error during classify: %s", exc, exc_info=True)
            return SLMClassification(
                error=f"unexpected: {exc}",
                latency_ms=latency_ms,
                model_available=False,
            )

    def generate(self, prompt: str, system: str | None = None) -> SLMResponse:
        """
        Generate a free-form response from the local SLM.
        Returns SLMResponse — never raises.
        """
        t0 = time.perf_counter()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self._client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0.7, "num_predict": 512},
            )
            text = response.message.content or ""
            latency_ms = (time.perf_counter() - t0) * 1000
            return SLMResponse(text=text, latency_ms=latency_ms, model_available=True)

        except ollama.ResponseError as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.warning("Ollama ResponseError during generate: %s", exc)
            return SLMResponse(
                text="[Local SLM unavailable — model error]",
                error=str(exc),
                latency_ms=latency_ms,
                model_available=True,
            )

        except ConnectionError as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.warning("Ollama not reachable during generate: %s", exc)
            return SLMResponse(
                text="[Local SLM unavailable — Ollama not running]",
                error="ollama_unavailable",
                latency_ms=latency_ms,
                model_available=False,
            )

        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - t0) * 1000
            logger.error("Unexpected error during generate: %s", exc, exc_info=True)
            return SLMResponse(
                text=f"[Local SLM error: {exc}]",
                error=str(exc),
                latency_ms=latency_ms,
                model_available=False,
            )

    def is_available(self) -> bool:
        """Return True if Ollama is reachable and the model exists."""
        try:
            models = self._client.list()
            names = [m.model for m in models.models]
            available = any(self.model in n for n in names)
            if not available:
                logger.warning(
                    "Model %r not found. Available: %s", self.model, names
                )
            return available
        except ConnectionError:
            return False
        except Exception:  # noqa: BLE001
            return False
