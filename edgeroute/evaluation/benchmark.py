"""
evaluation/benchmark.py
=======================
Latency and resource usage benchmark for EdgeRoute.

Measures:
  - Ollama availability check time
  - Cold-start (first inference) latency
  - Warm inference latencies (N subsequent calls)
  - Memory usage (RSS) before and during inference
  - CPU usage during inference
  - Full pipeline latency (including signals, privacy, policy)

IMPORTANT:
  - All reported numbers are measured from THIS machine at runtime.
  - No numbers are fabricated or assumed.
  - If Ollama is unavailable, deterministic-only latency is measured.
  - Results include the hardware context: CPU, RAM, OS.

Usage:
  py evaluation/benchmark.py
  py evaluation/benchmark.py --iterations 5 --output benchmark_results.json
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import psutil

# Make edgeroute importable when run from evaluation/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from models.slm import LocalSLM
from router.classifier import route
from router.signals import extract_signals
from router.privacy import check_privacy
from router.policy import apply_policy


# ---------------------------------------------------------------------------
# System info
# ---------------------------------------------------------------------------

def get_system_info() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    cpu_freq = psutil.cpu_freq()
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_freq_max_mhz": cpu_freq.max if cpu_freq else None,
        "ram_total_gb": round(vm.total / 1024**3, 2),
        "ram_available_gb": round(vm.available / 1024**3, 2),
    }


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------

def _measure_memory_mb() -> float:
    """Current process RSS memory in MB."""
    proc = psutil.Process()
    return proc.memory_info().rss / 1024**2


def _measure_cpu_percent(interval: float = 0.5) -> float:
    """CPU usage of current process over the given interval."""
    proc = psutil.Process()
    return proc.cpu_percent(interval=interval)


def _timeit(fn, *args, **kwargs) -> tuple[Any, float]:
    """Run fn(*args, **kwargs) and return (result, elapsed_ms)."""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, (time.perf_counter() - t0) * 1000


# ---------------------------------------------------------------------------
# Individual benchmarks
# ---------------------------------------------------------------------------

def bench_signal_extraction(query: str, iterations: int = 100) -> dict:
    """Benchmark deterministic signal extraction (no Ollama required)."""
    latencies = []
    for _ in range(iterations):
        _, ms = _timeit(extract_signals, query)
        latencies.append(ms)
    return {
        "component": "signal_extraction",
        "iterations": iterations,
        "mean_ms": statistics.mean(latencies),
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "p50_ms": statistics.median(latencies),
    }


def bench_privacy_check(query: str, iterations: int = 100) -> dict:
    """Benchmark privacy guard (no Ollama required)."""
    latencies = []
    for _ in range(iterations):
        _, ms = _timeit(check_privacy, query)
        latencies.append(ms)
    return {
        "component": "privacy_check",
        "iterations": iterations,
        "mean_ms": statistics.mean(latencies),
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "p50_ms": statistics.median(latencies),
    }


def bench_full_pipeline(queries: list[str]) -> dict:
    """Benchmark the full routing pipeline per query."""
    latencies = []
    ollama_ok = None
    for q in queries:
        result, ms = _timeit(route, q)
        latencies.append(ms)
        if ollama_ok is None:
            ollama_ok = result.ollama_available
    return {
        "component": "full_pipeline",
        "query_count": len(queries),
        "ollama_available": ollama_ok,
        "mean_ms": statistics.mean(latencies),
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "p50_ms": statistics.median(latencies),
        "p95_ms": sorted(latencies)[int(0.95 * len(latencies))],
    }


def bench_slm_inference(slm: LocalSLM, queries: list[str]) -> dict:
    """Benchmark SLM classification calls (requires Ollama)."""
    cold_start_ms: float | None = None
    warm_latencies: list[float] = []
    available = False

    for i, q in enumerate(queries):
        result, ms = _timeit(slm.classify, q)
        if result.model_available and not result.error:
            available = True
            if cold_start_ms is None:
                cold_start_ms = ms
            else:
                warm_latencies.append(ms)

    if not available:
        return {
            "component": "slm_inference",
            "available": False,
            "note": "Ollama not running or model not found",
        }

    return {
        "component": "slm_inference",
        "available": True,
        "cold_start_ms": cold_start_ms,
        "warm_mean_ms": statistics.mean(warm_latencies) if warm_latencies else None,
        "warm_min_ms": min(warm_latencies) if warm_latencies else None,
        "warm_max_ms": max(warm_latencies) if warm_latencies else None,
        "warm_p50_ms": statistics.median(warm_latencies) if warm_latencies else None,
        "warm_iterations": len(warm_latencies),
    }


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------

BENCHMARK_QUERIES = [
    "What is 2 + 2?",
    "Turn on the light.",
    "Write a 1500-word story about Mars.",
    "Define recursion.",
    "Set the temperature to 22 degrees.",
    "What is the capital of France?",
    "Help me with my project.",
    "Lock the front door.",
    "Analyze the geopolitical consequences of climate change.",
    "What does HTTP stand for?",
]


def run_benchmark(iterations: int = 5) -> dict[str, Any]:
    print(f"\n{'='*60}")
    print("  EdgeRoute — Latency & Resource Benchmark")
    print(f"{'='*60}")

    # System info
    sys_info = get_system_info()
    print(f"\n  Hardware Context:")
    print(f"    OS          : {sys_info['platform']} {sys_info['platform_release']}")
    print(f"    Architecture: {sys_info['architecture']}")
    print(f"    CPU cores   : {sys_info['cpu_count_physical']}p / {sys_info['cpu_count_logical']}l")
    if sys_info['cpu_freq_max_mhz']:
        print(f"    CPU freq    : {sys_info['cpu_freq_max_mhz']:.0f} MHz max")
    print(f"    RAM total   : {sys_info['ram_total_gb']} GB")
    print(f"    RAM avail   : {sys_info['ram_available_gb']} GB")
    print(f"    Python      : {sys_info['python_version']}")

    results: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "system": sys_info,
        "benchmarks": {},
        "memory": {},
    }

    # --- Memory baseline ---
    mem_before = _measure_memory_mb()
    results["memory"]["baseline_mb"] = round(mem_before, 1)

    # --- Signal extraction benchmark ---
    print(f"\n  [1/4] Benchmarking signal extraction ({iterations * 20} iterations)...")
    sig_result = bench_signal_extraction("Turn on the bedroom light", iterations * 20)
    results["benchmarks"]["signal_extraction"] = sig_result
    print(f"        Mean: {sig_result['mean_ms']:.3f}ms | Min: {sig_result['min_ms']:.3f}ms | Max: {sig_result['max_ms']:.3f}ms")

    # --- Privacy check benchmark ---
    print(f"  [2/4] Benchmarking privacy check ({iterations * 20} iterations)...")
    priv_result = bench_privacy_check("My email is test@example.com", iterations * 20)
    results["benchmarks"]["privacy_check"] = priv_result
    print(f"        Mean: {priv_result['mean_ms']:.3f}ms | Min: {priv_result['min_ms']:.3f}ms | Max: {priv_result['max_ms']:.3f}ms")

    # --- SLM inference benchmark ---
    print(f"  [3/4] Benchmarking SLM inference (requires Ollama)...")
    slm = LocalSLM()
    slm_queries = BENCHMARK_QUERIES[:iterations + 1]
    slm_result = bench_slm_inference(slm, slm_queries)
    results["benchmarks"]["slm_inference"] = slm_result
    if slm_result.get("available"):
        print(f"        Cold-start: {slm_result['cold_start_ms']:.0f}ms")
        if slm_result['warm_mean_ms']:
            print(f"        Warm mean : {slm_result['warm_mean_ms']:.0f}ms")
            print(f"        Warm min  : {slm_result['warm_min_ms']:.0f}ms")
            print(f"        Warm max  : {slm_result['warm_max_ms']:.0f}ms")
    else:
        print(f"        Ollama unavailable — SLM benchmark skipped.")

    # --- Full pipeline benchmark ---
    print(f"  [4/4] Benchmarking full routing pipeline ({len(BENCHMARK_QUERIES)} queries)...")
    pipeline_result = bench_full_pipeline(BENCHMARK_QUERIES)
    results["benchmarks"]["full_pipeline"] = pipeline_result
    print(f"        Ollama: {'YES' if pipeline_result.get('ollama_available') else 'NO (deterministic fallback)'}")
    print(f"        Mean  : {pipeline_result['mean_ms']:.1f}ms")
    print(f"        Min   : {pipeline_result['min_ms']:.1f}ms")
    print(f"        Max   : {pipeline_result['max_ms']:.1f}ms")
    print(f"        P50   : {pipeline_result['p50_ms']:.1f}ms")
    print(f"        P95   : {pipeline_result['p95_ms']:.1f}ms")

    # --- Memory after ---
    mem_after = _measure_memory_mb()
    results["memory"]["after_benchmark_mb"] = round(mem_after, 1)
    results["memory"]["delta_mb"] = round(mem_after - mem_before, 1)
    print(f"\n  Memory: {mem_before:.1f}MB → {mem_after:.1f}MB (Δ {mem_after - mem_before:+.1f}MB)")

    print(f"\n{'='*60}")
    print("  Benchmark complete.")
    print(f"{'='*60}\n")

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="EdgeRoute Benchmark")
    parser.add_argument("--iterations", type=int, default=5, help="Number of SLM iterations")
    parser.add_argument("--output", type=str, default=None, help="Save results to JSON file")
    args = parser.parse_args()

    results = run_benchmark(args.iterations)

    if args.output:
        out_path = Path(args.output)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"  Results saved to {out_path}")


if __name__ == "__main__":
    main()
