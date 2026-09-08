"""
tests/test_privacy.py
=====================
Unit tests for the privacy guard.
No Ollama or SLM required — fully deterministic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from router.privacy import check_privacy, PrivacyResult


# ---------------------------------------------------------------------------
# Test 1 — Clean query: no sensitive data
# ---------------------------------------------------------------------------

def test_clean_query_not_sensitive():
    result = check_privacy("What is the capital of France?")
    assert not result.is_sensitive
    assert result.detected_patterns == []
    assert not result.should_block_cloud


# ---------------------------------------------------------------------------
# Test 2 — Email address detected
# ---------------------------------------------------------------------------

def test_email_detected():
    result = check_privacy("My email is user@example.com, please help.")
    assert result.is_sensitive
    assert "email_address" in result.detected_patterns
    assert result.should_block_cloud


# ---------------------------------------------------------------------------
# Test 3 — Phone number detected
# ---------------------------------------------------------------------------

def test_phone_detected():
    result = check_privacy("Call me at +1-555-867-5309.")
    assert result.is_sensitive
    assert "phone_number" in result.detected_patterns


# ---------------------------------------------------------------------------
# Test 4 — Credit card number detected
# ---------------------------------------------------------------------------

def test_credit_card_detected():
    result = check_privacy("My credit card is 4111 1111 1111 1111.")
    assert result.is_sensitive
    assert "credit_card_number" in result.detected_patterns


# ---------------------------------------------------------------------------
# Test 5 — API key (OpenAI style) detected
# ---------------------------------------------------------------------------

def test_api_key_detected():
    result = check_privacy("Use API key sk-abc123def456ghi789jkl012mno345pqr to call the service.")
    assert result.is_sensitive
    assert "api_key_or_token" in result.detected_patterns


# ---------------------------------------------------------------------------
# Test 6 — Inline password detected
# ---------------------------------------------------------------------------

def test_password_detected():
    result = check_privacy("My password is hunter2. How do I reset it?")
    assert result.is_sensitive
    assert "inline_password" in result.detected_patterns


# ---------------------------------------------------------------------------
# Test 7 — SSN-like pattern detected
# ---------------------------------------------------------------------------

def test_ssn_detected():
    result = check_privacy("My SSN is 123-45-6789.")
    assert result.is_sensitive
    assert "ssn_like" in result.detected_patterns


# ---------------------------------------------------------------------------
# Test 8 — Multiple patterns in one query
# ---------------------------------------------------------------------------

def test_multiple_patterns():
    result = check_privacy(
        "Email: test@example.com. Card: 4111-1111-1111-1111. Call: +1-555-867-5309."
    )
    assert result.is_sensitive
    assert len(result.detected_patterns) >= 2


# ---------------------------------------------------------------------------
# Test 9 — Empty string is safe
# ---------------------------------------------------------------------------

def test_empty_string():
    result = check_privacy("")
    assert not result.is_sensitive


# ---------------------------------------------------------------------------
# Test 10 — Normal command query is safe
# ---------------------------------------------------------------------------

def test_command_query_safe():
    result = check_privacy("Turn on the bedroom light.")
    assert not result.is_sensitive


# ---------------------------------------------------------------------------
# Test 11 — Complex non-sensitive query is safe
# ---------------------------------------------------------------------------

def test_complex_safe_query():
    result = check_privacy(
        "Write a 1500-word story about a civilization on Mars that develops "
        "interstellar travel technology."
    )
    assert not result.is_sensitive


# ---------------------------------------------------------------------------
# Test 12 — Privacy result has correct blocked_reason when sensitive
# ---------------------------------------------------------------------------

def test_blocked_reason_populated():
    result = check_privacy("contact me at admin@corp.io")
    assert result.is_sensitive
    assert result.blocked_reason  # Not empty
    assert "email_address" in result.blocked_reason
