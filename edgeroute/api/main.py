"""
api/main.py
===========
EdgeRoute FastAPI backend.

Endpoints:
  POST /route     — Route a user query through the pipeline
  GET  /health    — Health check (Ollama + model status)
  GET  /telemetry — Routing statistics since startup

Run with:
  py -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
  (from the edgeroute/ directory)
"""
from __future__ import annotations

import logging
import sys
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

# Make project root importable when run from edgeroute/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import OLLAMA_HOST, OLLAMA_MODEL, MOCK_CLOUD
from models.slm import LocalSLM
from router.classifier import route as classifier_route

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edgeroute.api")

# ---------------------------------------------------------------------------
# In-memory telemetry (resets on server restart)
# ---------------------------------------------------------------------------

_telemetry: dict[str, Any] = {
    "total_requests": 0,
    "routes": defaultdict(int),
    "privacy_blocked": 0,
    "latencies_ms": [],
    "errors": 0,
    "startup_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
}


def _record(route: str, latency_ms: float, privacy_blocked: bool, error: bool) -> None:
    _telemetry["total_requests"] += 1
    _telemetry["routes"][route] += 1
    _telemetry["latencies_ms"].append(latency_ms)
    if privacy_blocked:
        _telemetry["privacy_blocked"] += 1
    if error:
        _telemetry["errors"] += 1
    # Keep only last 1000 latency values
    if len(_telemetry["latencies_ms"]) > 1000:
        _telemetry["latencies_ms"] = _telemetry["latencies_ms"][-1000:]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="EdgeRoute API",
    description=(
        "Local-First SLM Intelligence Router. "
        "Classification always runs locally — cloud is optional and post-routing only."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RouteRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000, description="User request to route")


class RouteResponse(BaseModel):
    route: str
    confidence: float
    reason_chain: list[str]
    response: str
    tool_result: dict | None
    latency_ms: float
    slm_latency_ms: float
    privacy_blocked: bool
    ollama_available: bool
    error: str
    signals: dict
    privacy: dict
    slm_classification: dict
    policy: dict


class HealthResponse(BaseModel):
    status: str
    ollama_host: str
    ollama_model: str
    ollama_reachable: bool
    model_available: bool
    mock_cloud: bool


class TelemetryResponse(BaseModel):
    total_requests: int
    route_counts: dict[str, int]
    privacy_blocked: int
    errors: int
    avg_latency_ms: float | None
    startup_time: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/route", response_model=RouteResponse)
async def route_query(body: RouteRequest) -> RouteResponse:
    """
    Route a user query through the EdgeRoute pipeline.

    Classification always happens locally.
    Cloud adapter is only called (optionally) for CLOUD_COMPLEX routes.
    """
    try:
        result = classifier_route(body.query)
        _record(
            result.final_route,
            result.latency_ms,
            result.privacy_blocked,
            bool(result.error),
        )
        return RouteResponse(
            route=result.final_route,
            confidence=result.confidence,
            reason_chain=result.reason_chain,
            response=result.response,
            tool_result=result.tool_result,
            latency_ms=result.latency_ms,
            slm_latency_ms=result.slm_latency_ms,
            privacy_blocked=result.privacy_blocked,
            ollama_available=result.ollama_available,
            error=result.error,
            signals=result.signals.to_dict() if result.signals else {},
            privacy={
                "is_sensitive": result.privacy.is_sensitive if result.privacy else False,
                "detected_patterns": result.privacy.detected_patterns if result.privacy else [],
                "blocked_reason": result.privacy.blocked_reason if result.privacy else "",
            },
            slm_classification={
                "route": result.slm_classification.route if result.slm_classification else "",
                "confidence": result.slm_classification.confidence if result.slm_classification else 0.0,
                "reason": result.slm_classification.reason if result.slm_classification else "",
                "intent": result.slm_classification.intent if result.slm_classification else "",
                "error": result.slm_classification.error if result.slm_classification else "",
            },
            policy={
                "final_route": result.policy.final_route if result.policy else "",
                "confidence": result.policy.confidence if result.policy else 0.0,
                "overridden": result.policy.overridden if result.policy else False,
                "override_reason": result.policy.override_reason if result.policy else "",
                "reason_chain": result.policy.reason_chain if result.policy else [],
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Error in /route: %s", exc, exc_info=True)
        _record("AMBIGUOUS", 0.0, False, True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    Checks Ollama connectivity and model availability.
    """
    slm = LocalSLM()
    try:
        reachable = True
        available = slm.is_available()
    except Exception:
        reachable = False
        available = False

    return HealthResponse(
        status="ok",
        ollama_host=OLLAMA_HOST,
        ollama_model=OLLAMA_MODEL,
        ollama_reachable=reachable,
        model_available=available,
        mock_cloud=MOCK_CLOUD,
    )


@app.get("/telemetry", response_model=TelemetryResponse)
async def get_telemetry() -> TelemetryResponse:
    """Return routing telemetry since server startup."""
    lats = _telemetry["latencies_ms"]
    avg_lat = sum(lats) / len(lats) if lats else None
    return TelemetryResponse(
        total_requests=_telemetry["total_requests"],
        route_counts=dict(_telemetry["routes"]),
        privacy_blocked=_telemetry["privacy_blocked"],
        errors=_telemetry["errors"],
        avg_latency_ms=round(avg_lat, 2) if avg_lat is not None else None,
        startup_time=_telemetry["startup_time"],
    )


@app.get("/")
async def root() -> dict:
    return {
        "name": "EdgeRoute",
        "subtitle": "Local-First AI Inference Router",
        "tagline": "Decide locally. Execute locally when possible. Escalate only when necessary.",
        "docs": "/docs",
        "health": "/health",
    }
