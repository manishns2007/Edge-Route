"""
router/classifier.py
====================
Classifier orchestrator — the central pipeline that chains together all
routing components and returns a single RoutingResult.

Pipeline:
  1. Preprocess query (validate, strip)
  2. Extract signals (router.signals)
  3. Privacy scan (router.privacy)
  4. Local SLM classification (models.slm)
  5. Policy evaluation (router.policy)
  6. Response generation (local SLM / tools / cloud adapter)

The final RoutingResult is a fully self-contained explanation of the
routing decision, suitable for displaying in the UI and logging.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ALLOWED_TOOLS
from models.slm import LocalSLM, SLMClassification
from router.policy import PolicyDecision, apply_policy
from router.privacy import PrivacyResult, check_privacy
from router.signals import SignalResult, extract_signals

logger = logging.getLogger(__name__)

# Lazy singleton — instantiated on first use to avoid import-time Ollama calls
_slm_instance: LocalSLM | None = None


def _get_slm() -> LocalSLM:
    global _slm_instance
    if _slm_instance is None:
        _slm_instance = LocalSLM()
    return _slm_instance


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class RoutingResult:
    """
    Complete result of the routing pipeline.

    Every field is populated regardless of which route was chosen, making
    the result fully explainable in the UI and evaluation scripts.
    """
    # Core routing decision
    final_route: str = "AMBIGUOUS"
    confidence: float = 0.0

    # Pipeline components
    signals: SignalResult | None = None
    privacy: PrivacyResult | None = None
    slm_classification: SLMClassification | None = None
    policy: PolicyDecision | None = None

    # Explainability
    reason_chain: list[str] = field(default_factory=list)

    # Execution result (tool output, SLM response, cloud response)
    response: str = ""
    tool_result: dict[str, Any] | None = None

    # Timing
    latency_ms: float = 0.0
    slm_latency_ms: float = 0.0

    # Status flags
    privacy_blocked: bool = False
    ollama_available: bool = True
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (for FastAPI responses)."""
        return {
            "final_route": self.final_route,
            "confidence": round(self.confidence, 4),
            "reason_chain": self.reason_chain,
            "response": self.response,
            "tool_result": self.tool_result,
            "latency_ms": round(self.latency_ms, 2),
            "slm_latency_ms": round(self.slm_latency_ms, 2),
            "privacy_blocked": self.privacy_blocked,
            "ollama_available": self.ollama_available,
            "error": self.error,
            "signals": self.signals.to_dict() if self.signals else {},
            "privacy": {
                "is_sensitive": self.privacy.is_sensitive if self.privacy else False,
                "detected_patterns": self.privacy.detected_patterns if self.privacy else [],
                "blocked_reason": self.privacy.blocked_reason if self.privacy else "",
            },
            "slm_classification": {
                "route": self.slm_classification.route if self.slm_classification else "",
                "confidence": self.slm_classification.confidence if self.slm_classification else 0.0,
                "reason": self.slm_classification.reason if self.slm_classification else "",
                "intent": self.slm_classification.intent if self.slm_classification else "",
                "error": self.slm_classification.error if self.slm_classification else "",
            } if self.slm_classification else {},
            "policy": {
                "final_route": self.policy.final_route if self.policy else "",
                "confidence": self.policy.confidence if self.policy else 0.0,
                "overridden": self.policy.overridden if self.policy else False,
                "override_reason": self.policy.override_reason if self.policy else "",
            } if self.policy else {},
        }


# ---------------------------------------------------------------------------
# Main routing function
# ---------------------------------------------------------------------------

def route(
    query: str,
    slm: LocalSLM | None = None,
) -> RoutingResult:
    """
    Route a user query through the full EdgeRoute pipeline.

    Parameters
    ----------
    query:
        The raw user request string.
    slm:
        Optional LocalSLM instance (uses singleton if None).

    Returns
    -------
    RoutingResult — always returns, never raises.
    """
    pipeline_start = time.perf_counter()
    result = RoutingResult()

    # ------------------------------------------------------------------
    # Step 1 — Preprocess
    # ------------------------------------------------------------------
    query = (query or "").strip()
    if not query:
        result.final_route = "AMBIGUOUS"
        result.confidence = 1.0
        result.reason_chain = ["Empty query received."]
        result.response = "Please enter a request."
        result.latency_ms = (time.perf_counter() - pipeline_start) * 1000
        return result

    # ------------------------------------------------------------------
    # Step 2 — Feature extraction
    # ------------------------------------------------------------------
    signals = extract_signals(query)
    result.signals = signals
    result.reason_chain.append(
        f"Extracted signals: {signals.word_count} words, "
        f"complexity={signals.complexity_score:.2f}, "
        f"command={signals.is_command:.2f}, tool={signals.is_tool:.2f}."
    )

    # ------------------------------------------------------------------
    # Step 3 — Privacy scan
    # ------------------------------------------------------------------
    privacy = check_privacy(query)
    result.privacy = privacy
    if privacy.is_sensitive:
        result.reason_chain.append(
            f"Privacy guard: sensitive patterns detected "
            f"({', '.join(privacy.detected_patterns)})."
        )
        result.privacy_blocked = True

    # ------------------------------------------------------------------
    # Step 4 — Local SLM classification
    # ------------------------------------------------------------------
    _slm = slm or _get_slm()
    slm_result = _slm.classify(query)
    result.slm_classification = slm_result
    result.slm_latency_ms = slm_result.latency_ms
    result.ollama_available = slm_result.model_available

    if slm_result.error:
        result.reason_chain.append(f"SLM error: {slm_result.error}")
    else:
        result.reason_chain.append(
            f"SLM classified: {slm_result.route} "
            f"(confidence={slm_result.confidence:.2f}, reason='{slm_result.reason}')."
        )

    # ------------------------------------------------------------------
    # Step 5 — Policy evaluation
    # ------------------------------------------------------------------
    policy = apply_policy(slm_result, signals, privacy)
    result.policy = policy
    result.reason_chain.extend(policy.reason_chain)

    final_route = policy.final_route
    final_conf = policy.confidence
    result.final_route = final_route
    result.confidence = final_conf

    # ------------------------------------------------------------------
    # Step 6 — Execute the selected route
    # ------------------------------------------------------------------
    if final_route == "LOCAL_COMMAND":
        result.response, result.tool_result = _execute_local_command(query, signals)
        result.reason_chain.append(
            f"Executed local tool: {result.tool_result.get('tool', 'unknown') if result.tool_result else 'dispatch failed'}."
        )

    elif final_route == "LOCAL_SIMPLE":
        if slm_result.model_available and not slm_result.error:
            slm_resp = _slm.generate(query)
            result.response = slm_resp.text or "[No response from local SLM]"
            result.slm_latency_ms += slm_resp.latency_ms
            result.reason_chain.append("Generated response using local SLM.")
        else:
            result.response = (
                "[Local SLM unavailable — Ollama is not running. "
                "Start Ollama and pull qwen2.5:0.5b to enable local inference.]"
            )
            result.reason_chain.append("Local SLM unavailable; returning placeholder response.")

    elif final_route == "CLOUD_COMPLEX":
        if privacy.is_sensitive:
            result.response = (
                "🔒 Cloud escalation blocked by local privacy policy. "
                f"Reason: {privacy.blocked_reason}"
            )
            result.reason_chain.append("Cloud response blocked due to privacy.")
        else:
            result.response = _call_cloud(query)
            result.reason_chain.append("Response obtained from cloud adapter.")

    else:  # AMBIGUOUS
        result.response = (
            "I'm not sure how to handle this request. "
            "Could you please provide more context or be more specific?"
        )
        result.reason_chain.append("Request is ambiguous; asking user for clarification.")

    # ------------------------------------------------------------------
    # Final timing
    # ------------------------------------------------------------------
    result.latency_ms = (time.perf_counter() - pipeline_start) * 1000
    logger.info(
        "route(%r) → %s (conf=%.2f, %.0fms)",
        query[:60],
        final_route,
        final_conf,
        result.latency_ms,
    )
    return result


# ---------------------------------------------------------------------------
# Local command execution
# ---------------------------------------------------------------------------

def _execute_local_command(
    query: str,
    signals: SignalResult,
) -> tuple[str, dict[str, Any] | None]:
    """Dispatch to the appropriate local tool based on query keywords."""
    # Import here to avoid circular imports
    from tools.local_tools import dispatch_command

    tool_result = dispatch_command(query)
    if tool_result and tool_result.get("status") == "success":
        response = f"✅ {tool_result['message']}"
    elif tool_result:
        response = f"⚠️ Tool execution: {tool_result.get('message', 'unknown result')}"
    else:
        response = "⚠️ Could not identify the appropriate local tool for this command."

    return response, tool_result


# ---------------------------------------------------------------------------
# Cloud adapter call
# ---------------------------------------------------------------------------

def _call_cloud(query: str) -> str:
    """Call the cloud adapter (may be mocked)."""
    from cloud.adapter import CloudLLMAdapter

    adapter = CloudLLMAdapter()
    cloud_resp = adapter.generate(query)
    return cloud_resp.text
