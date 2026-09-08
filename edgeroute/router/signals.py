"""
router/signals.py
=================
Local, deterministic feature extraction from a user query.

All computation is local — no SLM calls, no external APIs.
These signals SUPPLEMENT the SLM classification and allow the
policy layer to enforce routing rules deterministically.

Returns a typed SignalResult dataclass and a plain dict.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

# ---------------------------------------------------------------------------
# Keyword lists — kept as module-level constants for easy maintenance
# ---------------------------------------------------------------------------

_QUESTION_STARTERS = re.compile(
    r"^\s*(what|who|where|when|why|how|which|whose|is|are|was|were|"
    r"do|does|did|can|could|would|should|will|shall|may|might|tell me)\b",
    re.IGNORECASE,
)

_COMMAND_VERBS = re.compile(
    r"\b(turn (on|off)|set|start|stop|play|pause|lock|unlock|open|close|"
    r"adjust|activate|deactivate|enable|disable|run|execute|launch|switch|"
    r"connect|disconnect|restart|reboot|dim|brighten|mute|unmute)\b",
    re.IGNORECASE,
)

_TOOL_KEYWORDS = re.compile(
    r"\b(light|fan|temperature|thermostat|music|door|alarm|camera|"
    r"device|appliance|sensor|speaker|heater|cooler|air conditioner|"
    r"ac|tv|television|radio|blinds|curtains|lock|garage)\b",
    re.IGNORECASE,
)

_CODE_KEYWORDS = re.compile(
    r"\b(code|program|function|class|algorithm|implement|debug|fix|"
    r"error|exception|syntax|compile|script|library|framework|api|"
    r"database|query|sql|html|css|javascript|python|java|c\+\+|"
    r"typescript|golang|rust|bash|shell|git|docker|kubernetes|"
    r"microservice|endpoint|repository|pull request|refactor|unit test)\b",
    re.IGNORECASE,
)

_REASONING_KEYWORDS = re.compile(
    r"\b(analyze|analyse|explain|compare|contrast|evaluate|assess|"
    r"discuss|argue|justify|critique|implications|consequences|impact|"
    r"geopolitical|philosophy|ethics|strategy|architecture|design|"
    r"scalable|distributed|trade-off|pros and cons|advantages|"
    r"disadvantages|recommend|suggest improvements|review)\b",
    re.IGNORECASE,
)

_CREATIVE_KEYWORDS = re.compile(
    r"\b(write|create|generate|compose|draft|story|poem|essay|article|"
    r"novel|script|narrative|fiction|creative|imaginative|describe in detail|"
    r"character|plot|setting|dialogue|song|lyrics|blog post|report)\b",
    re.IGNORECASE,
)

_MATH_KEYWORDS = re.compile(
    r"\b(calculate|compute|solve|equation|formula|integral|derivative|"
    r"matrix|vector|statistics|probability|algebra|geometry|trigonometry|"
    r"calculus|arithmetic|sum|product|average|median|variance|"
    r"standard deviation)\b|\d+\s*[\+\-\*\/\^\%]\s*\d+",
    re.IGNORECASE,
)

_SENSITIVE_KEYWORDS = re.compile(
    r"\b(password|secret|api[_\s]?key|token|credential|ssn|social security|"
    r"credit card|bank account|private key|passphrase|auth|bearer|"
    r"access key|secret key)\b",
    re.IGNORECASE,
)

_AMBIGUITY_PHRASES = re.compile(
    r"\b(this|it|that|these|those|something|anything|everything|help me|"
    r"make it|fix it|do something|make this better|improve this|"
    r"what should i do|not sure|whatever|somehow|kind of)\b",
    re.IGNORECASE,
)

_LONG_OUTPUT_INDICATORS = re.compile(
    r"\b(\d{3,}[\s-]?word|thousand[s]?\s+word|long[\s-]?form|"
    r"detailed (report|analysis|essay|story|explanation)|"
    r"comprehensive|in-depth|exhaustive|thorough|step[- ]by[- ]step guide|"
    r"full (tutorial|guide|documentation))\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SignalResult:
    """Structured feature extraction result."""
    # Basic stats
    char_count: int = 0
    word_count: int = 0
    sentence_count: int = 0

    # Signal scores (0.0 – 1.0 range; boolean signals encoded as 0/1)
    is_question: float = 0.0
    is_command: float = 0.0
    is_code_request: float = 0.0
    is_reasoning: float = 0.0
    is_creative: float = 0.0
    is_math: float = 0.0
    is_tool: float = 0.0
    is_sensitive: float = 0.0
    is_ambiguous: float = 0.0
    expects_long_output: float = 0.0

    # Derived composite score
    complexity_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def likely_command(self) -> bool:
        """True when both command verb AND tool/device keyword detected."""
        return self.is_command > 0.4 and self.is_tool > 0.4

    @property
    def likely_complex(self) -> bool:
        """True when complexity score is meaningfully high."""
        return self.complexity_score > 0.65


# ---------------------------------------------------------------------------
# Extraction function
# ---------------------------------------------------------------------------

def extract_signals(query: str) -> SignalResult:
    """
    Extract lightweight deterministic signals from a user query.

    All computation is local, deterministic, and runs in microseconds.
    Returns a SignalResult dataclass.
    """
    q = query.strip()

    # --- Basic stats ---
    char_count = len(q)
    words = q.split()
    word_count = len(words)
    # Rough sentence count
    sentence_count = max(1, len(re.split(r"[.!?]+", q)))

    # --- Boolean / graded signals ---
    def _score(pattern: re.Pattern, text: str, multiplier: float = 1.0) -> float:
        matches = len(pattern.findall(text))
        return min(1.0, matches * multiplier)

    is_question = 1.0 if _QUESTION_STARTERS.match(q) or q.rstrip().endswith("?") else 0.0

    is_command = min(1.0, _score(_COMMAND_VERBS, q, 0.6))
    is_tool = min(1.0, _score(_TOOL_KEYWORDS, q, 0.5))
    is_code_request = min(1.0, _score(_CODE_KEYWORDS, q, 0.25))
    is_reasoning = min(1.0, _score(_REASONING_KEYWORDS, q, 0.3))
    is_creative = min(1.0, _score(_CREATIVE_KEYWORDS, q, 0.25))
    is_math = min(1.0, _score(_MATH_KEYWORDS, q, 0.4))
    is_sensitive = min(1.0, _score(_SENSITIVE_KEYWORDS, q, 0.7))
    is_ambiguous = min(1.0, _score(_AMBIGUITY_PHRASES, q, 0.25))
    expects_long_output = min(1.0, _score(_LONG_OUTPUT_INDICATORS, q, 0.8))

    # Word count contributes to long-output signal
    if word_count > 50:
        expects_long_output = min(1.0, expects_long_output + 0.3)
    elif word_count > 30:
        expects_long_output = min(1.0, expects_long_output + 0.1)

    # --- Composite complexity score ---
    # Weighted combination of signals that indicate a task is too complex for
    # the local SLM; used by the policy layer as a hard override signal.
    complexity_score = min(
        1.0,
        (
            0.25 * is_reasoning
            + 0.20 * is_code_request
            + 0.20 * is_creative
            + 0.15 * expects_long_output
            + 0.10 * (word_count / 100.0)  # long queries are often complex
            + 0.10 * is_math
        ),
    )

    return SignalResult(
        char_count=char_count,
        word_count=word_count,
        sentence_count=sentence_count,
        is_question=is_question,
        is_command=is_command,
        is_code_request=is_code_request,
        is_reasoning=is_reasoning,
        is_creative=is_creative,
        is_math=is_math,
        is_tool=is_tool,
        is_sensitive=is_sensitive,
        is_ambiguous=is_ambiguous,
        expects_long_output=expects_long_output,
        complexity_score=complexity_score,
    )
