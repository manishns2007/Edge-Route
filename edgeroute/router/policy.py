"""
router/policy.py
================
Deterministic Policy Engine — the safety and sanity layer that sits BETWEEN
the SLM classification and the final routing decision.

The policy engine validates and potentially OVERRIDES the SLM's decision
using hard rules.  It is the component that ensures:

  1. Low-confidence SLM outputs are downgraded to AMBIGUOUS.
  2. Strong command signals always route to LOCAL_COMMAND.
  3. Privacy-sensitive requests never reach the cloud adapter.
  4. Strong complexity signals can escalate to CLOUD_COMPLEX even if the
     SLM classified the request otherwise.
  5. Malformed or missing SLM output falls back safely to AMBIGUOUS.
  6. Unknown route labels from the SLM are normalised to AMBIGUOUS.

Final routing decision formula:
  Final Decision = SLM classification
                 + extracted signals
                 + deterministic safety/policy rules
"""
from __future__ import annotations

import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field

from config import (
    SLM_CONFIDENCE_THRESHOLD,
    COMPLEXITY_THRESHOLD,
    COMPLEXITY_WORD_THRESHOLD,
    VALID_ROUTES,
)
from models.slm import SLMClassification
from router.privacy import PrivacyResult
from router.signals import SignalResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PolicyDecision:
    """Result produced by the policy engine."""
    final_route: str = "AMBIGUOUS"
    confidence: float = 0.0
    overridden: bool = False
    override_reason: str = ""
    reason_chain: list[str] = field(default_factory=list)

    @property
    def is_cloud(self) -> bool:
        return self.final_route == "CLOUD_COMPLEX"

    @property
    def is_local_command(self) -> bool:
        return self.final_route == "LOCAL_COMMAND"


# ---------------------------------------------------------------------------
# Policy engine
# ---------------------------------------------------------------------------

def apply_policy(
    slm_result: SLMClassification,
    signals: SignalResult,
    privacy_result: PrivacyResult,
    confidence_threshold: float | None = None,
    complexity_threshold: float | None = None,
) -> PolicyDecision:
    """
    Apply deterministic routing rules on top of the SLM classification.

    Parameters
    ----------
    slm_result:
        The raw classification from the local SLM (may contain errors).
    signals:
        Extracted deterministic signals from the query.
    privacy_result:
        Privacy scan result for the query.
    confidence_threshold:
        Override the global threshold (used in tests).
    complexity_threshold:
        Override the global complexity threshold (used in tests).

    Returns
    -------
    PolicyDecision
    """
    conf_thresh = confidence_threshold if confidence_threshold is not None else SLM_CONFIDENCE_THRESHOLD
    complex_thresh = complexity_threshold if complexity_threshold is not None else COMPLEXITY_THRESHOLD

    reason_chain: list[str] = []
    override_reason = ""
    overridden = False

    # Determine base route and confidence from SLM
    slm_route = slm_result.route
    slm_conf = slm_result.confidence
    slm_error = slm_result.error

    # -----------------------------------------------------------------------
    # RULE 0 — Ollama / model unavailable → deterministic fallback
    # -----------------------------------------------------------------------
    if slm_error == "ollama_unavailable" or not slm_result.model_available:
        reason_chain.append("Ollama is unavailable; using deterministic fallback.")
        base_route, base_conf = _deterministic_route(signals, reason_chain)
        overridden = True
        override_reason = "ollama_unavailable"
    elif slm_error:
        reason_chain.append(f"SLM returned an error ({slm_error}); using deterministic fallback.")
        base_route, base_conf = _deterministic_route(signals, reason_chain)
        overridden = True
        override_reason = slm_error
    elif slm_route not in VALID_ROUTES:
        reason_chain.append(f"SLM returned unknown route '{slm_route}'; normalising to AMBIGUOUS.")
        base_route, base_conf = "AMBIGUOUS", 0.0
        overridden = True
        override_reason = "unknown_route"
    else:
        base_route = slm_route
        base_conf = slm_conf
        reason_chain.append(f"SLM classified as {slm_route} (confidence={slm_conf:.2f}).")

    # -----------------------------------------------------------------------
    # RULE 1 — Confidence threshold
    # Low-confidence SLM → replace with deterministic fallback
    # -----------------------------------------------------------------------
    if not overridden and base_conf < conf_thresh:
        reason_chain.append(
            f"SLM confidence ({base_conf:.2f}) below threshold ({conf_thresh:.2f}); "
            "falling back to deterministic routing."
        )
        det_route, det_conf = _deterministic_route(signals, reason_chain)
        base_route = det_route
        base_conf = det_conf
        overridden = True
        override_reason = "low_confidence"

    # -----------------------------------------------------------------------
    # RULE 2 — Command intent override
    # Strong command + tool signal → always LOCAL_COMMAND
    # -----------------------------------------------------------------------
    if signals.likely_command:
        if base_route != "LOCAL_COMMAND":
            reason_chain.append(
                "Strong command verb + tool/device keyword detected — "
                f"overriding {base_route} → LOCAL_COMMAND."
            )
            overridden = True
            override_reason = "command_intent_override"
        else:
            reason_chain.append("Command intent confirmed by signal extraction.")
        base_route = "LOCAL_COMMAND"
        base_conf = max(base_conf, 0.90)

    # -----------------------------------------------------------------------
    # RULE 3 — Privacy enforcement
    # Sensitive data → never send to cloud
    # -----------------------------------------------------------------------
    if privacy_result.is_sensitive:
        if base_route == "CLOUD_COMPLEX":
            reason_chain.append(
                f"Privacy guard blocked cloud escalation: {privacy_result.blocked_reason}"
            )
            base_route = "LOCAL_SIMPLE"
            base_conf = 0.95
            overridden = True
            override_reason = "privacy_block"
        else:
            reason_chain.append(
                "Privacy guard active: sensitive patterns detected but route "
                f"is already {base_route} — no change needed."
            )

    # -----------------------------------------------------------------------
    # RULE 4 — Complexity override
    # High complexity score or very long query → escalate to CLOUD_COMPLEX
    # (unless privacy-blocked)
    # -----------------------------------------------------------------------
    if (
        not privacy_result.is_sensitive
        and base_route not in ("LOCAL_COMMAND", "CLOUD_COMPLEX")
        and (
            signals.complexity_score >= complex_thresh
            or signals.word_count >= COMPLEXITY_WORD_THRESHOLD
        )
    ):
        reason_chain.append(
            f"High complexity score ({signals.complexity_score:.2f}) or long query "
            f"({signals.word_count} words) — escalating to CLOUD_COMPLEX."
        )
        base_route = "CLOUD_COMPLEX"
        base_conf = max(base_conf, 0.80)
        overridden = True
        override_reason = override_reason or "complexity_override"

    # -----------------------------------------------------------------------
    # RULE 5 — Sensitive signal without privacy pattern match
    # If signals detected sensitive keywords, keep LOCAL_SIMPLE
    # -----------------------------------------------------------------------
    if signals.is_sensitive > 0.5 and not privacy_result.is_sensitive:
        if base_route == "CLOUD_COMPLEX":
            reason_chain.append(
                "Sensitive keyword detected in query; downgrading from CLOUD_COMPLEX → LOCAL_SIMPLE."
            )
            base_route = "LOCAL_SIMPLE"
            base_conf = 0.80
            overridden = True
            override_reason = override_reason or "sensitive_keyword"

    # -----------------------------------------------------------------------
    # Final assembly
    # -----------------------------------------------------------------------
    logger.debug(
        "Policy decision: %s (conf=%.2f, overridden=%s)",
        base_route, base_conf, overridden,
    )

    return PolicyDecision(
        final_route=base_route,
        confidence=round(base_conf, 4),
        overridden=overridden,
        override_reason=override_reason,
        reason_chain=reason_chain,
    )


# ---------------------------------------------------------------------------
# Deterministic routing (when SLM is unavailable or low-confidence)
# ---------------------------------------------------------------------------

def _deterministic_route(
    signals: SignalResult,
    reason_chain: list[str],
) -> tuple[str, float]:
    """
    Produce a routing decision using only extracted signals.
    Used as fallback when the SLM is unavailable or untrustworthy.
    """
    # Command — highest priority for deterministic routing
    if signals.likely_command:
        reason_chain.append("Deterministic: command verb + tool/device keyword → LOCAL_COMMAND.")
        return "LOCAL_COMMAND", 0.88

    # Clearly complex
    if signals.complexity_score >= COMPLEXITY_THRESHOLD or signals.word_count >= COMPLEXITY_WORD_THRESHOLD:
        reason_chain.append(
            f"Deterministic: high complexity ({signals.complexity_score:.2f}) → CLOUD_COMPLEX."
        )
        return "CLOUD_COMPLEX", 0.78

    # Simple question or math
    if signals.is_question > 0.5 or signals.is_math > 0.5:
        if signals.word_count <= 20 and signals.complexity_score < 0.3:
            reason_chain.append("Deterministic: short question or arithmetic → LOCAL_SIMPLE.")
            return "LOCAL_SIMPLE", 0.80

    # Short, low-complexity queries without other strong signals are probably LOCAL_SIMPLE
    # (e.g. "Define recursion.", "Convert 5 km to meters.", "What is DNA?")
    if (
        signals.word_count <= 15
        and signals.complexity_score < 0.2
        and signals.is_creative < 0.3
        and signals.is_reasoning < 0.3
        and signals.expects_long_output < 0.2
    ):
        reason_chain.append(
            "Deterministic: short, low-complexity query → LOCAL_SIMPLE."
        )
        return "LOCAL_SIMPLE", 0.75

    # Ambiguous
    reason_chain.append("Deterministic: insufficient signals → AMBIGUOUS.")
    return "AMBIGUOUS", 0.50
