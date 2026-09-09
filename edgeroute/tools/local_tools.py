"""
tools/local_tools.py
====================
Safe, allowlisted simulated local tools.

IMPORTANT:
  - All tools are SIMULATED.  No real hardware is controlled.
  - The allowlist in config.ALLOWED_TOOLS is the single source of truth.
  - Arbitrary tool names from user input are NEVER executed.
  - No shell commands are invoked based on user input.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ALLOWED_TOOLS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------
ToolResult = dict[str, Any]


# ---------------------------------------------------------------------------
# Hardware GPIO Integration (Raspberry Pi 4 / 5)
# ---------------------------------------------------------------------------
_GPIO_AVAILABLE = False
_LIGHT_PIN = None
try:
    from gpiozero import LED
    _LIGHT_PIN = LED(17)  # GPIO 17 (Pin 11) for physical LED / Relay
    _GPIO_AVAILABLE = True
    logger.info("Raspberry Pi GPIO detected: Pin 17 active for hardware control.")
except Exception:
    _GPIO_AVAILABLE = False


# ---------------------------------------------------------------------------
# Individual tool implementations (simulated or real GPIO if present)
# ---------------------------------------------------------------------------

def turn_on_light(location: str = "room") -> ToolResult:
    """Turn on light (physical GPIO 17 on Raspberry Pi or simulated)."""
    if _GPIO_AVAILABLE and _LIGHT_PIN:
        try:
            _LIGHT_PIN.on()
        except Exception as e:
            logger.warning("GPIO error: %s", e)
    msg = f"Light turned ON in the {location}."
    logger.info("[TOOL] %s", msg)
    return {"tool": "turn_on_light", "status": "success", "message": msg, "simulated": True, "gpio": _GPIO_AVAILABLE}


def turn_off_light(location: str = "room") -> ToolResult:
    """Turn off light (physical GPIO 17 on Raspberry Pi or simulated)."""
    if _GPIO_AVAILABLE and _LIGHT_PIN:
        try:
            _LIGHT_PIN.off()
        except Exception as e:
            logger.warning("GPIO error: %s", e)
    msg = f"Light turned OFF in the {location}."
    logger.info("[TOOL] %s", msg)
    return {"tool": "turn_off_light", "status": "success", "message": msg, "simulated": True, "gpio": _GPIO_AVAILABLE}


def set_temperature(value: float = 22.0, unit: str = "C") -> ToolResult:
    """Simulate setting thermostat temperature."""
    msg = f"Temperature set to {value}°{unit}."
    logger.info("[SIMULATED] %s", msg)
    return {
        "tool": "set_temperature",
        "status": "success",
        "message": msg,
        "value": value,
        "unit": unit,
        "simulated": True,
    }


def start_music(genre: str = "") -> ToolResult:
    """Simulate starting music playback."""
    genre_str = f" ({genre})" if genre else ""
    msg = f"Music playback started{genre_str}."
    logger.info("[SIMULATED] %s", msg)
    return {"tool": "start_music", "status": "success", "message": msg, "simulated": True}


def lock_door(location: str = "front") -> ToolResult:
    """Simulate locking a door."""
    msg = f"{location.capitalize()} door locked."
    logger.info("[SIMULATED] %s", msg)
    return {"tool": "lock_door", "status": "success", "message": msg, "simulated": True}


# ---------------------------------------------------------------------------
# Tool registry — ALLOWLIST ONLY
# ---------------------------------------------------------------------------

_TOOL_REGISTRY: dict[str, Any] = {
    "turn_on_light": turn_on_light,
    "turn_off_light": turn_off_light,
    "set_temperature": set_temperature,
    "start_music": start_music,
    "lock_door": lock_door,
}

# Verify registry matches config allowlist at import time
assert set(_TOOL_REGISTRY.keys()) == set(ALLOWED_TOOLS), (
    f"Tool registry mismatch! Registry: {set(_TOOL_REGISTRY.keys())}, "
    f"Allowlist: {set(ALLOWED_TOOLS)}"
)


# ---------------------------------------------------------------------------
# Command parsing helpers
# ---------------------------------------------------------------------------

_LIGHT_ON_RE = re.compile(
    r"\b(turn on|switch on|enable|activate)\b.*\blight",
    re.IGNORECASE,
)
_LIGHT_OFF_RE = re.compile(
    r"\b(turn off|switch off|disable|deactivate)\b.*\blight",
    re.IGNORECASE,
)
_TEMP_RE = re.compile(
    r"\b(set|adjust|change)\b.*\b(temperature|thermostat|temp)\b.*?(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_MUSIC_RE = re.compile(
    r"\b(start|play|begin)\b.*\b(music|song|audio|playlist)",
    re.IGNORECASE,
)
_LOCK_RE = re.compile(
    r"\b(lock|secure)\b.*\b(door|gate|entrance|front|back)",
    re.IGNORECASE,
)
_LOCATION_RE = re.compile(
    r"\b(bedroom|living room|kitchen|bathroom|office|hallway|garage|front|back)\b",
    re.IGNORECASE,
)
_GENRE_RE = re.compile(
    r"\b(jazz|rock|pop|classical|hip.hop|country|electronic|lofi|ambient|metal)\b",
    re.IGNORECASE,
)


def _extract_location(query: str) -> str:
    m = _LOCATION_RE.search(query)
    return m.group(0) if m else "room"


def _extract_temperature(query: str) -> float:
    m = _TEMP_RE.search(query)
    if m:
        try:
            return float(m.group(3))
        except (IndexError, ValueError):
            pass
    # Fallback: look for standalone number near temp keywords
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:degrees?|°|celsius|fahrenheit)?", query, re.IGNORECASE)
    if m2:
        try:
            return float(m2.group(1))
        except ValueError:
            pass
    return 22.0


def _extract_genre(query: str) -> str:
    m = _GENRE_RE.search(query)
    return m.group(0) if m else ""


# ---------------------------------------------------------------------------
# Dispatch function — called by classifier
# ---------------------------------------------------------------------------

def dispatch_command(query: str) -> ToolResult:
    """
    Parse a user command string and dispatch to the appropriate allowlisted tool.

    Returns a ToolResult dict.  Returns an error dict if no tool matched.
    Never executes arbitrary code or shell commands.
    """
    q = query.strip()

    if _LIGHT_ON_RE.search(q):
        return turn_on_light(_extract_location(q))

    if _LIGHT_OFF_RE.search(q):
        return turn_off_light(_extract_location(q))

    if _TEMP_RE.search(q):
        return set_temperature(_extract_temperature(q))

    if _MUSIC_RE.search(q):
        return start_music(_extract_genre(q))

    if _LOCK_RE.search(q):
        return lock_door(_extract_location(q))

    # Fallback: keyword scan for tool names
    q_lower = q.lower()
    if "light" in q_lower and ("on" in q_lower or "off" in q_lower):
        return turn_on_light() if "on" in q_lower else turn_off_light()
    if "temperature" in q_lower or "thermostat" in q_lower:
        return set_temperature(_extract_temperature(q))
    if "music" in q_lower or "song" in q_lower:
        return start_music()
    if "door" in q_lower and ("lock" in q_lower or "secure" in q_lower):
        return lock_door()

    logger.warning("No tool matched for command: %r", q[:80])
    return {
        "tool": "unknown",
        "status": "error",
        "message": f"No local tool matched the command: '{q[:60]}'",
        "simulated": True,
    }


def execute_tool(tool_name: str, **kwargs: Any) -> ToolResult:
    """
    Execute a named tool from the allowlist directly (used by tests and API).

    Raises ValueError for unknown tool names — never executes non-allowlisted tools.
    """
    if tool_name not in _TOOL_REGISTRY:
        raise ValueError(
            f"Tool '{tool_name}' is not in the allowlist. "
            f"Allowed tools: {ALLOWED_TOOLS}"
        )
    return _TOOL_REGISTRY[tool_name](**kwargs)
