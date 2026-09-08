"""
main.py
=======
EdgeRoute CLI entrypoint.

Usage:
  py main.py                          # Interactive mode
  py main.py "What is 2 + 2?"        # Single query
  py main.py --check                  # Health check only
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure edgeroute package is importable when run from this directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)


def _print_result(query: str, result) -> None:
    """Pretty-print a RoutingResult to stdout."""
    route_icons = {
        "LOCAL_SIMPLE": "[GREEN]",
        "LOCAL_COMMAND": "[BLUE]",
        "CLOUD_COMPLEX": "[RED]",
        "AMBIGUOUS": "[YELLOW]",
    }
    icon = route_icons.get(result.final_route, "[?]")
    sep = "-" * 60
    print(f"\n{sep}")
    print(f"  Query     : {query[:80]}")
    print(f"  Route     : {icon} {result.final_route}")
    print(f"  Confidence: {result.confidence*100:.0f}%")
    print(f"  Latency   : {result.latency_ms:.0f} ms")
    if result.privacy_blocked:
        print(f"  [LOCK] Privacy: CLOUD ESCALATION BLOCKED")
        print(f"    Patterns: {', '.join(result.privacy.detected_patterns)}")
    if result.final_route == "LOCAL_COMMAND" and result.tool_result:
        tr = result.tool_result
        print(f"  Tool      : {tr.get('tool', '?')} -> {tr.get('status', '?').upper()}")
        print(f"  Message   : {tr.get('message', '')}")
    print(f"  Response  : {result.response[:200]}")
    print(f"\n  Reason chain:")
    for step in result.reason_chain:
        print(f"    - {step}")
    print(f"{sep}\n")


def _health_check() -> None:
    from models.slm import LocalSLM
    from config import OLLAMA_HOST, OLLAMA_MODEL, MOCK_CLOUD

    print(f"\nEdgeRoute Health Check")
    print(f"  Ollama host : {OLLAMA_HOST}")
    print(f"  Model       : {OLLAMA_MODEL}")
    print(f"  Cloud mode  : {'MOCK' if MOCK_CLOUD else 'LIVE'}")

    slm = LocalSLM()
    if slm.is_available():
        print(f"  Ollama      : ✅ Running — model '{OLLAMA_MODEL}' available")
    else:
        print(f"  Ollama      : ⚠️  Not reachable or model not found")
        print(f"  → Start Ollama and run: ollama pull {OLLAMA_MODEL}")
    print()


def _interactive_mode() -> None:
    from router.classifier import route

    print("\n" + "="*60)
    print("  EdgeRoute — Local-First AI Inference Router")
    print("  Type a request, or 'quit' to exit.")
    print("="*60)

    while True:
        try:
            query = input("\n  Your request: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Goodbye!")
            break

        if query.lower() in ("quit", "exit", "q"):
            print("  Goodbye!")
            break

        if not query:
            continue

        result = route(query)
        _print_result(query, result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EdgeRoute — Local-First AI Inference Router",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py main.py                              # Interactive mode
  py main.py "What is 2 + 2?"            # Single query
  py main.py "Turn on the light."        # Local command
  py main.py --check                     # Health check
  py main.py --json "Define recursion."  # JSON output
        """,
    )
    parser.add_argument("query", nargs="?", help="Query to route (optional)")
    parser.add_argument("--check", action="store_true", help="Run health check and exit")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    if args.check:
        _health_check()
        return

    if args.query:
        from router.classifier import route
        result = route(args.query)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_result(args.query, result)
    else:
        _interactive_mode()


if __name__ == "__main__":
    main()
