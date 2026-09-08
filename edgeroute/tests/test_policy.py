"""
tests/test_policy.py
====================
Unit tests for the deterministic policy engine.
No SLM or Ollama required.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.slm import SLMClassification
from router.policy import apply_policy, PolicyDecision
from router.privacy import PrivacyResult
from router.signals import SignalResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cls(route="LOCAL_SIMPLE", conf=0.95, error="", available=True) -> SLMClassification:
    return SLMClassification(
        route=route, confidence=conf, error=error,
        reason="test", intent="test", model_available=available
    )

def _signals(**kwargs) -> SignalResult:
    defaults = dict(
        char_count=20, word_count=5, sentence_count=1,
        is_question=0.0, is_command=0.0, is_code_request=0.0,
        is_reasoning=0.0, is_creative=0.0, is_math=0.0,
        is_tool=0.0, is_sensitive=0.0, is_ambiguous=0.0,
        expects_long_output=0.0, complexity_score=0.0,
    )
    defaults.update(kwargs)
    return SignalResult(**defaults)

def _no_privacy() -> PrivacyResult:
    return PrivacyResult()

def _privacy_hit(patterns=("email_address",)) -> PrivacyResult:
    return PrivacyResult(
        is_sensitive=True,
        detected_patterns=list(patterns),
        blocked_reason="Test privacy hit",
    )


# ---------------------------------------------------------------------------
# Test 1 — High-confidence SLM result passes through unchanged
# ---------------------------------------------------------------------------

def test_high_confidence_passes_through():
    decision = apply_policy(_cls("LOCAL_SIMPLE", 0.95), _signals(), _no_privacy())
    assert decision.final_route == "LOCAL_SIMPLE"
    assert not decision.overridden


# ---------------------------------------------------------------------------
# Test 2 — Low-confidence triggers deterministic fallback
# ---------------------------------------------------------------------------

def test_low_confidence_triggers_fallback():
    decision = apply_policy(
        _cls("CLOUD_COMPLEX", 0.30),
        _signals(is_question=1.0, word_count=5),
        _no_privacy(),
        confidence_threshold=0.70,
    )
    assert decision.overridden
    assert decision.override_reason == "low_confidence"
    # Deterministic should pick LOCAL_SIMPLE for a short question
    assert decision.final_route in ("LOCAL_SIMPLE", "AMBIGUOUS")


# ---------------------------------------------------------------------------
# Test 3 — Command override: strong command + tool signals override SLM
# ---------------------------------------------------------------------------

def test_command_override():
    decision = apply_policy(
        _cls("LOCAL_SIMPLE", 0.90),
        _signals(is_command=0.6, is_tool=0.5),
        _no_privacy(),
    )
    assert decision.final_route == "LOCAL_COMMAND"
    assert decision.overridden
    assert decision.override_reason == "command_intent_override"


# ---------------------------------------------------------------------------
# Test 4 — Privacy blocks cloud escalation
# ---------------------------------------------------------------------------

def test_privacy_blocks_cloud():
    decision = apply_policy(
        _cls("CLOUD_COMPLEX", 0.90),
        _signals(),
        _privacy_hit(),
    )
    assert decision.final_route != "CLOUD_COMPLEX"
    assert decision.overridden
    assert decision.override_reason == "privacy_block"


# ---------------------------------------------------------------------------
# Test 5 — Privacy does NOT affect local routes
# ---------------------------------------------------------------------------

def test_privacy_does_not_affect_local_simple():
    decision = apply_policy(
        _cls("LOCAL_SIMPLE", 0.90),
        _signals(),
        _privacy_hit(),
    )
    # LOCAL_SIMPLE should remain unchanged even with privacy hit
    assert decision.final_route == "LOCAL_SIMPLE"


# ---------------------------------------------------------------------------
# Test 6 — Complexity override escalates to CLOUD_COMPLEX
# ---------------------------------------------------------------------------

def test_complexity_override_escalates():
    decision = apply_policy(
        _cls("LOCAL_SIMPLE", 0.85),
        _signals(complexity_score=0.80, word_count=30),
        _no_privacy(),
        complexity_threshold=0.70,
    )
    assert decision.final_route == "CLOUD_COMPLEX"
    assert decision.overridden


# ---------------------------------------------------------------------------
# Test 7 — Complexity override blocked by privacy
# ---------------------------------------------------------------------------

def test_complexity_override_blocked_by_privacy():
    decision = apply_policy(
        _cls("CLOUD_COMPLEX", 0.88),
        _signals(complexity_score=0.85),
        _privacy_hit(),
    )
    # Privacy should win: cloud blocked
    assert decision.final_route != "CLOUD_COMPLEX"
    assert decision.overridden


# ---------------------------------------------------------------------------
# Test 8 — Ollama unavailable → deterministic fallback
# ---------------------------------------------------------------------------

def test_ollama_unavailable_fallback():
    slm_cls = SLMClassification(
        error="ollama_unavailable", model_available=False
    )
    decision = apply_policy(
        slm_cls,
        _signals(is_command=0.6, is_tool=0.5),
        _no_privacy(),
    )
    assert decision.overridden
    assert decision.override_reason == "ollama_unavailable"
    # With command signals, should pick LOCAL_COMMAND
    assert decision.final_route == "LOCAL_COMMAND"


# ---------------------------------------------------------------------------
# Test 9 — Unknown route label from SLM → normalise to AMBIGUOUS
# ---------------------------------------------------------------------------

def test_unknown_route_normalised():
    bad_cls = SLMClassification(route="WHATEVER_ROUTE", confidence=0.99)
    decision = apply_policy(bad_cls, _signals(), _no_privacy())
    assert decision.overridden
    assert decision.override_reason == "unknown_route"


# ---------------------------------------------------------------------------
# Test 10 — SLM error → deterministic routing
# ---------------------------------------------------------------------------

def test_slm_error_triggers_deterministic():
    err_cls = SLMClassification(
        route="AMBIGUOUS",
        confidence=0.0,
        error="json_parse_failure",
        model_available=True,
    )
    decision = apply_policy(err_cls, _signals(is_question=1.0, word_count=4), _no_privacy())
    assert decision.overridden
    assert "json_parse_failure" in decision.override_reason
