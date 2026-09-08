"""
tests/test_tools.py
===================
Unit tests for local tool execution.
No Ollama required — tools are deterministic simulations.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.local_tools import (
    dispatch_command,
    execute_tool,
    turn_on_light,
    turn_off_light,
    set_temperature,
    start_music,
    lock_door,
)


# ---------------------------------------------------------------------------
# Test 1 — turn_on_light default
# ---------------------------------------------------------------------------

def test_turn_on_light_default():
    result = turn_on_light()
    assert result["tool"] == "turn_on_light"
    assert result["status"] == "success"
    assert "on" in result["message"].lower()
    assert result["simulated"] is True


# ---------------------------------------------------------------------------
# Test 2 — turn_on_light with location
# ---------------------------------------------------------------------------

def test_turn_on_light_with_location():
    result = turn_on_light("bedroom")
    assert result["status"] == "success"
    assert "bedroom" in result["message"].lower()


# ---------------------------------------------------------------------------
# Test 3 — turn_off_light
# ---------------------------------------------------------------------------

def test_turn_off_light():
    result = turn_off_light("kitchen")
    assert result["tool"] == "turn_off_light"
    assert result["status"] == "success"
    assert "off" in result["message"].lower()


# ---------------------------------------------------------------------------
# Test 4 — set_temperature
# ---------------------------------------------------------------------------

def test_set_temperature():
    result = set_temperature(24.0, "C")
    assert result["tool"] == "set_temperature"
    assert result["status"] == "success"
    assert result["value"] == 24.0
    assert result["unit"] == "C"
    assert "24" in result["message"]


# ---------------------------------------------------------------------------
# Test 5 — start_music default
# ---------------------------------------------------------------------------

def test_start_music_default():
    result = start_music()
    assert result["tool"] == "start_music"
    assert result["status"] == "success"
    assert "started" in result["message"].lower()


# ---------------------------------------------------------------------------
# Test 6 — start_music with genre
# ---------------------------------------------------------------------------

def test_start_music_with_genre():
    result = start_music("jazz")
    assert result["status"] == "success"
    assert "jazz" in result["message"].lower()


# ---------------------------------------------------------------------------
# Test 7 — lock_door
# ---------------------------------------------------------------------------

def test_lock_door():
    result = lock_door("front")
    assert result["tool"] == "lock_door"
    assert result["status"] == "success"
    assert "front" in result["message"].lower()
    assert "locked" in result["message"].lower()


# ---------------------------------------------------------------------------
# Test 8 — dispatch_command: turn on light
# ---------------------------------------------------------------------------

def test_dispatch_turn_on_light():
    result = dispatch_command("Turn on the bedroom light.")
    assert result["tool"] == "turn_on_light"
    assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Test 9 — dispatch_command: set temperature
# ---------------------------------------------------------------------------

def test_dispatch_set_temperature():
    result = dispatch_command("Set the temperature to 22 degrees.")
    assert result["tool"] == "set_temperature"
    assert result["status"] == "success"
    assert result["value"] == 22.0


# ---------------------------------------------------------------------------
# Test 10 — dispatch_command: lock door
# ---------------------------------------------------------------------------

def test_dispatch_lock_door():
    result = dispatch_command("Lock the front door.")
    assert result["tool"] == "lock_door"
    assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Test 11 — dispatch_command: start music with genre
# ---------------------------------------------------------------------------

def test_dispatch_start_music():
    result = dispatch_command("Play some jazz music.")
    assert result["tool"] == "start_music"
    assert result["status"] == "success"


# ---------------------------------------------------------------------------
# Test 12 — dispatch_command: unrecognised command returns error dict
# ---------------------------------------------------------------------------

def test_dispatch_unknown_command():
    result = dispatch_command("Fly me to the moon at warp speed.")
    assert result["status"] == "error"
    assert result["tool"] == "unknown"


# ---------------------------------------------------------------------------
# Test 13 — execute_tool: valid tool
# ---------------------------------------------------------------------------

def test_execute_tool_valid():
    result = execute_tool("turn_on_light", location="office")
    assert result["status"] == "success"
    assert "office" in result["message"].lower()


# ---------------------------------------------------------------------------
# Test 14 — execute_tool: invalid tool raises ValueError
# ---------------------------------------------------------------------------

def test_execute_tool_invalid_raises():
    with pytest.raises(ValueError, match="not in the allowlist"):
        execute_tool("rm_rf_everything")


# ---------------------------------------------------------------------------
# Test 15 — All simulated results have simulated=True flag
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fn,args", [
    (turn_on_light, []),
    (turn_off_light, []),
    (set_temperature, [22.0]),
    (start_music, []),
    (lock_door, []),
])
def test_all_tools_marked_simulated(fn, args):
    result = fn(*args)
    assert result["simulated"] is True
