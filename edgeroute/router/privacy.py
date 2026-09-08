"""
router/privacy.py
=================
Lightweight local privacy guard for demonstration purposes.

DISCLAIMER: This is a heuristic pattern-matching implementation designed to
demonstrate the concept of local privacy-aware routing.  It is NOT a
production-grade PII detection system.  For production use, integrate a
dedicated tool such as Microsoft Presidio, Google DLP, or a fine-tuned NER
model.

The guard inspects queries for common sensitive data patterns BEFORE any
cloud escalation can occur.  Detected sensitive data blocks CLOUD_COMPLEX
routing and forces LOCAL_SIMPLE or LOCAL_ONLY handling.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Regex patterns
# Each entry: (label, compiled pattern)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Email addresses
    (
        "email_address",
        re.compile(
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
        ),
    ),
    # Phone numbers (US-style and international variants)
    (
        "phone_number",
        re.compile(
            r"(\+?\d{1,3}[\s\-\.]?)?\(?\d{2,4}\)?[\s\-\.]?\d{3,4}[\s\-\.]?\d{4}"
        ),
    ),
    # Credit-card-like 16-digit numbers (various separators)
    (
        "credit_card_number",
        re.compile(
            r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"
        ),
    ),
    # API keys / tokens (common prefixes)
    (
        "api_key_or_token",
        re.compile(
            r"\b(sk-[A-Za-z0-9]{20,}|"
            r"pk_(?:live|test)_[A-Za-z0-9]{20,}|"
            r"ghp_[A-Za-z0-9]{30,}|"
            r"ya29\.[A-Za-z0-9_\-]+|"
            r"AKIA[A-Z0-9]{16}|"
            r"Bearer\s+[A-Za-z0-9_\-\.]+|"
            r"[Aa][Pp][Ii][-_]?[Kk][Ee][Yy]\s*[:=]\s*\S{8,})\b",
            re.IGNORECASE,
        ),
    ),
    # Passwords stated in clear (heuristic: "password is …" or "password: …" or "password = …")
    (
        "inline_password",
        re.compile(
            r"\b(password|passwd|passphrase|secret)\s*(?:is|was|[:=\s])\s*\S{4,}",
            re.IGNORECASE,
        ),
    ),
    # SSN-like patterns (US format)
    (
        "ssn_like",
        re.compile(
            r"\b\d{3}[\s\-]\d{2}[\s\-]\d{4}\b"
        ),
    ),
    # Government ID / national ID (generic heuristic)
    (
        "government_id_like",
        re.compile(
            r"\b([A-Z]{1,2}\d{6,9}|\d{8,12})\b"  # passport / driving licence patterns
        ),
    ),
    # Private/secret key mentions
    (
        "key_mention",
        re.compile(
            r"\b(private[\s_]?key|secret[\s_]?key|access[\s_]?key|"
            r"auth[\s_]?token|refresh[\s_]?token)\b",
            re.IGNORECASE,
        ),
    ),
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PrivacyResult:
    """Result of a privacy scan on a user query."""
    is_sensitive: bool = False
    detected_patterns: list[str] = field(default_factory=list)
    blocked_reason: str = ""

    @property
    def should_block_cloud(self) -> bool:
        """Return True when this request must NOT be forwarded to the cloud."""
        return self.is_sensitive


# ---------------------------------------------------------------------------
# Detection function
# ---------------------------------------------------------------------------

def check_privacy(query: str) -> PrivacyResult:
    """
    Scan a query for sensitive information patterns.

    DISCLAIMER: Lightweight local privacy guard for demonstration purposes.
    Not a production-grade PII detector.

    Returns a PrivacyResult.  Never raises.
    """
    if not query:
        return PrivacyResult()

    detected: list[str] = []
    for label, pattern in _PATTERNS:
        if pattern.search(query):
            detected.append(label)

    if detected:
        reason = (
            f"Detected sensitive pattern(s): {', '.join(detected)}. "
            "Cloud escalation blocked by local privacy policy."
        )
        return PrivacyResult(
            is_sensitive=True,
            detected_patterns=detected,
            blocked_reason=reason,
        )

    return PrivacyResult()
