"""
app/ui.py
=========
EdgeRoute — Real-Time Local-First AI Inference Router UI
State-of-the-Art Glassmorphic Dark Interface
"""
from __future__ import annotations

import sys
import os
import time
from pathlib import Path
from collections import Counter, deque

# Make edgeroute/ importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration — MUST be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="EdgeRoute — Real-Time AI Router",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# State-of-the-Art Glassmorphic Dark Theme CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* === Google Fonts === */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* === Global Reset === */
html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* === Fix Streamlit White Header Bar Glitch === */
header[data-testid="stHeader"], .stAppHeader, div[data-testid="stToolbar"] {
    background: transparent !important;
    background-color: transparent !important;
    color: #e2e8f0 !important;
}

/* === Deep Space Mesh Gradient Background === */
.stApp {
    background-color: #060810 !important;
    background-image: 
        radial-gradient(circle at 15% 15%, rgba(59, 130, 246, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(139, 92, 246, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.04) 0%, transparent 50%) !important;
    color: #f1f5f9 !important;
}

/* === Custom Header / Hero === */
.er-hero {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 24px 32px;
    margin-bottom: 24px;
    box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(20px);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
}
.er-hero-title {
    font-size: 2.2rem;
    font-weight: 800;
    margin: 0;
    background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.8px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.er-hero-tagline {
    color: #94a3b8;
    margin: 6px 0 0;
    font-size: 0.95rem;
    font-weight: 400;
}
.er-status-pill {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 9999px;
    padding: 6px 16px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #34d399;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.15);
}
.er-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.85); }
}

/* === Glassmorphic Cards === */
.er-card {
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 20px;
    backdrop-filter: blur(16px);
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    transition: border-color 0.2s ease;
}
.er-card:hover {
    border-color: rgba(255, 255, 255, 0.15);
}
.er-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}
.er-card-title {
    color: #94a3b8;
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* === Route Badges === */
.badge-glow {
    padding: 12px 24px;
    border-radius: 14px;
    font-weight: 800;
    font-size: 1.15rem;
    letter-spacing: 0.5px;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
}
.badge-local-simple {
    background: linear-gradient(135deg, rgba(5, 150, 105, 0.8) 0%, rgba(16, 185, 129, 0.6) 100%);
    border: 1px solid #34d399;
    color: #ecfdf5;
    box-shadow: 0 0 25px rgba(16, 185, 129, 0.35);
}
.badge-local-command {
    background: linear-gradient(135deg, rgba(30, 58, 138, 0.8) 0%, rgba(37, 99, 235, 0.6) 100%);
    border: 1px solid #60a5fa;
    color: #eff6ff;
    box-shadow: 0 0 25px rgba(37, 99, 235, 0.35);
}
.badge-cloud-complex {
    background: linear-gradient(135deg, rgba(159, 18, 57, 0.8) 0%, rgba(225, 29, 72, 0.6) 100%);
    border: 1px solid #fb7185;
    color: #fff1f2;
    box-shadow: 0 0 25px rgba(225, 29, 72, 0.35);
}
.badge-privacy {
    background: linear-gradient(135deg, rgba(88, 28, 135, 0.8) 0%, rgba(147, 51, 234, 0.6) 100%);
    border: 1px solid #c084fc;
    color: #faf5ff;
    box-shadow: 0 0 25px rgba(147, 51, 234, 0.35);
}
.badge-ambiguous {
    background: linear-gradient(135deg, rgba(146, 64, 14, 0.8) 0%, rgba(217, 119, 6, 0.6) 100%);
    border: 1px solid #fbbf24;
    color: #fffbeb;
    box-shadow: 0 0 25px rgba(217, 119, 6, 0.35);
}

/* === Metric Boxes === */
.stat-box {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}
.stat-box-val {
    font-size: 1.9rem;
    font-weight: 800;
    color: #f8fafc;
    line-height: 1.1;
    font-family: 'JetBrains Mono', monospace;
}
.stat-box-lbl {
    font-size: 0.72rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 6px;
}

/* === Architecture Pipeline Flow Indicator === */
.pipeline-flow {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 12px 18px;
    margin-bottom: 22px;
    overflow-x: auto;
    gap: 8px;
}
.pipeline-node {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #64748b;
    padding: 6px 12px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.02);
    white-space: nowrap;
}
.pipeline-node-active {
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.3);
    box-shadow: 0 0 12px rgba(56, 189, 248, 0.2);
}
.pipeline-node-target {
    color: #34d399;
    background: rgba(52, 211, 153, 0.12);
    border: 1px solid rgba(52, 211, 153, 0.3);
    box-shadow: 0 0 12px rgba(52, 211, 153, 0.2);
}
.pipeline-arrow {
    color: #475569;
    font-size: 0.85rem;
}

/* === Response Container === */
.response-container {
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 24px;
    font-size: 1.05rem;
    line-height: 1.7;
    color: #f8fafc;
}

/* === Reason Item === */
.reason-step {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 10px 14px;
    background: rgba(255, 255, 255, 0.02);
    border-left: 3px solid #6366f1;
    border-radius: 0 8px 8px 0;
    margin-bottom: 8px;
    font-size: 0.88rem;
    color: #cbd5e1;
}

/* === Quick Chips === */
.chip-btn {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #cbd5e1 !important;
    border-radius: 20px !important;
    padding: 6px 14px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.chip-btn:hover {
    border-color: #818cf8 !important;
    color: #ffffff !important;
    transform: translateY(-1px) !important;
}

/* === Streamlit Inputs Override === */
.stTextArea textarea {
    background: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 14px !important;
    color: #f8fafc !important;
    font-size: 1.05rem !important;
    line-height: 1.6 !important;
    padding: 16px !important;
    transition: all 0.2s ease !important;
}
.stTextArea textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 20px rgba(99, 102, 241, 0.25) !important;
}
.stButton > button {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    padding: 14px 28px !important;
    box-shadow: 0 8px 25px -5px rgba(79, 70, 229, 0.5) !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 30px -5px rgba(79, 70, 229, 0.7) !important;
}

/* === Sidebar Styling === */
section[data-testid="stSidebar"] {
    background: rgba(10, 14, 26, 0.95) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
def _init_state():
    defaults = {
        "history": deque(maxlen=50),
        "route_counter": Counter(),
        "total_requests": 0,
        "privacy_blocked": 0,
        "total_latency_ms": 0.0,
        "last_result": None,
        "main_input": "",
        "auto_route": False,
        "device_state": {
            "Living Room Light": "OFF",
            "Bedroom Light": "OFF",
            "Thermostat": "22°C",
            "Front Door": "LOCKED",
        }
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ---------------------------------------------------------------------------
# Header / Hero Section
# ---------------------------------------------------------------------------
from config import OLLAMA_HOST, OLLAMA_MODEL, MOCK_CLOUD
from models.slm import LocalSLM

# Check live Ollama availability
_active_model = st.session_state.get("selected_model", OLLAMA_MODEL)
_slm = LocalSLM(model=_active_model)
_is_ollama_online = _slm.is_available()

status_label = f"OLLAMA ONLINE · {str(_active_model).upper()}" if _is_ollama_online else "OLLAMA OFFLINE (FALLBACK MODE)"
status_color = "#10b981" if _is_ollama_online else "#ef4444"
pill_bg = "rgba(16, 185, 129, 0.12)" if _is_ollama_online else "rgba(239, 68, 68, 0.12)"
pill_border = "rgba(16, 185, 129, 0.35)" if _is_ollama_online else "rgba(239, 68, 68, 0.35)"

st.markdown(f"""
<div class="er-hero">
  <div>
    <div class="er-hero-title">⚡ EdgeRoute</div>
    <div class="er-hero-tagline">Real-Time Autonomous Local-First Inference Orchestrator</div>
  </div>
  <div style="background:{pill_bg}; border:1px solid {pill_border}; border-radius:9999px; padding:6px 16px; font-size:0.82rem; font-weight:600; color:{status_color}; display:flex; align-items:center; gap:8px;">
    <div style="width:8px; height:8px; border-radius:50%; background-color:{status_color}; box-shadow:0 0 8px {status_color};"></div>
    {status_label}
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar: Engine Settings & Real-Time Device State
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    
    # Model Selector
    available_models = ["llama3.2:3b", "qwen2.5:0.5b"]
    chosen_model = st.selectbox(
        "Active Local SLM",
        available_models,
        index=0 if _active_model == "llama3.2:3b" else 1,
        help="Select the local model hosted via Ollama."
    )
    if chosen_model != st.session_state.get("selected_model"):
        st.session_state["selected_model"] = chosen_model
        os.environ["OLLAMA_MODEL"] = chosen_model
        st.rerun()

    # Cloud Escalation Configuration
    st.markdown("---")
    st.markdown("### ☁️ Cloud Provider Keys")
    cloud_key_input = st.text_input(
        "OpenAI / Groq API Key",
        value=os.getenv("CLOUD_API_KEY", ""),
        type="password",
        placeholder="sk-...",
        help="Provide an API key to enable live cloud LLM escalation for complex tasks."
    )
    if cloud_key_input:
        os.environ["CLOUD_API_KEY"] = cloud_key_input
        os.environ["MOCK_CLOUD"] = "false"
        st.caption("🟢 Live Cloud Escalation Enabled")
    else:
        st.caption("ℹ️ No key set: complex tasks use local high-capacity fallback.")

    # Smart Home Device State Viewer
    st.markdown("---")
    st.markdown("### 🏠 IoT Devices State")
    for device, state in st.session_state["device_state"].items():
        state_color = "#34d399" if state in ("ON", "UNLOCKED") else ("#60a5fa" if "°" in state else "#94a3b8")
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 10px; background:rgba(255,255,255,0.03); border-radius:8px; margin-bottom:6px; font-size:0.85rem;">
          <span style="color:#cbd5e1;">{device}</span>
          <span style="font-weight:700; color:{state_color}; font-family:'JetBrains Mono';">{state}</span>
        </div>
        """, unsafe_allow_html=True)

    # Session Stats
    st.markdown("---")
    st.markdown("### 📊 Session Telemetry")
    tot = st.session_state["total_requests"]
    if tot > 0:
        avg_lat = st.session_state["total_latency_ms"] / tot
        st.metric("Total Routed", tot)
        st.metric("Avg Latency", f"{avg_lat:.0f} ms")
        st.metric("Privacy Protected", st.session_state["privacy_blocked"])
    else:
        st.caption("No queries routed in this session.")

# ---------------------------------------------------------------------------
# Quick Action Test Chips
# ---------------------------------------------------------------------------
st.markdown("##### ⚡ Quick Test Queries")
chip_cols = st.columns(6)
SAMPLE_PROMPTS = [
    ("🔢 Math Query", "What is 200 + 0"),
    ("💡 Device Command", "Turn on the living room light."),
    ("🌡️ Thermostat", "Set the temperature to 21 degrees."),
    ("☁️ Deep Reasoning", "Explain the difference between quantum computing and classical computing simply."),
    ("🔒 Privacy Shield", "My email is user@secure-corp.com and key is sk-live999, summarize my profile."),
    ("❓ Ambiguous", "Help me fix this error right now."),
]

for col, (label, prompt_text) in zip(chip_cols, SAMPLE_PROMPTS):
    with col:
        if st.button(label, key=f"chip_{label}", use_container_width=True):
            st.session_state["main_input"] = prompt_text
            st.session_state["auto_route"] = True
            st.rerun()

# ---------------------------------------------------------------------------
# Main Input Area
# ---------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
user_query = st.text_area(
    "Query Input",
    height=110,
    placeholder="Type any prompt: arithmetic ('200 + 0'), smart device command ('Turn on bedroom light'), complex question, or sensitive data...",
    key="main_input",
    label_visibility="collapsed",
)

col_btn, col_info = st.columns([1, 2])
with col_btn:
    route_btn = st.button("🔀 Route & Execute Pipeline", use_container_width=True)

should_route = route_btn or st.session_state.pop("auto_route", False)

# ---------------------------------------------------------------------------
# Route Execution Pipeline
# ---------------------------------------------------------------------------
if should_route:
    query_to_route = st.session_state.get("main_input", "").strip()
    if not query_to_route:
        st.warning("⚠️ Please enter a prompt first.")
    else:
        with st.spinner("⚡ Running local signals, privacy inspection, and neural routing..."):
            from router.classifier import route as classifier_route
            # Pass custom model if chosen
            active_slm = LocalSLM(model=st.session_state.get("selected_model", OLLAMA_MODEL))
            result = classifier_route(query_to_route, slm=active_slm)

        # Update Smart Home State if command executed
        if result.final_route == "LOCAL_COMMAND" and result.tool_result:
            tr = result.tool_result
            tool_name = tr.get("tool", "")
            loc = tr.get("location", "living room").lower()
            
            if "turn_on_light" in tool_name:
                key = "Bedroom Light" if "bed" in loc else "Living Room Light"
                st.session_state["device_state"][key] = "ON"
            elif "turn_off_light" in tool_name:
                key = "Bedroom Light" if "bed" in loc else "Living Room Light"
                st.session_state["device_state"][key] = "OFF"
            elif "set_temperature" in tool_name:
                val = tr.get("value", 22)
                st.session_state["device_state"]["Thermostat"] = f"{val}°C"
            elif "lock_door" in tool_name:
                st.session_state["device_state"]["Front Door"] = "LOCKED"

        # Update Telemetry & History
        st.session_state["last_result"] = (query_to_route, result)
        st.session_state["total_requests"] += 1
        st.session_state["total_latency_ms"] += result.latency_ms
        st.session_state["route_counter"][result.final_route] += 1
        if result.privacy_blocked:
            st.session_state["privacy_blocked"] += 1
            
        st.session_state["history"].appendleft({
            "query": query_to_route[:60] + ("…" if len(query_to_route) > 60 else ""),
            "route": result.final_route,
            "conf": result.confidence,
            "latency": result.latency_ms,
            "privacy": result.privacy_blocked,
        })

# ---------------------------------------------------------------------------
# Display Results
# ---------------------------------------------------------------------------
if st.session_state.get("last_result"):
    query_display, result = st.session_state["last_result"]

    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Visual Pipeline Breadcrumbs
    route_target = result.final_route
    slm_target_class = "pipeline-node-target" if route_target == "LOCAL_SIMPLE" else ""
    cmd_target_class = "pipeline-node-target" if route_target == "LOCAL_COMMAND" else ""
    cloud_target_class = "pipeline-node-target" if route_target == "CLOUD_COMPLEX" else ""
    privacy_target_class = "pipeline-node-target" if result.privacy_blocked else ""

    st.markdown(f"""
    <div class="pipeline-flow">
      <div class="pipeline-node pipeline-node-active">📥 Input Query</div>
      <div class="pipeline-arrow">➔</div>
      <div class="pipeline-node pipeline-node-active">🔍 Signal Scanner</div>
      <div class="pipeline-arrow">➔</div>
      <div class="pipeline-node {'pipeline-node-target' if result.privacy_blocked else 'pipeline-node-active'}">🛡️ Privacy Shield</div>
      <div class="pipeline-arrow">➔</div>
      <div class="pipeline-node pipeline-node-active">🧠 Neural Classifier</div>
      <div class="pipeline-arrow">➔</div>
      <div class="pipeline-node pipeline-node-active">⚖️ Policy Arbiter</div>
      <div class="pipeline-arrow">➔</div>
      <div class="pipeline-node pipeline-node-target">🎯 {result.final_route}</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Privacy Alert Banner if Blocked
    if result.privacy_blocked:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg, rgba(147, 51, 234, 0.2) 0%, rgba(219, 39, 119, 0.15) 100%); border:1px solid #c084fc; border-radius:14px; padding:16px 22px; margin-bottom:20px; color:#f3e8ff; display:flex; align-items:center; gap:14px;">
          <div style="font-size:1.8rem;">🔒</div>
          <div>
            <strong style="font-size:1.05rem;">Cloud Escalation Blocked by Privacy Shield</strong><br>
            <span style="color:#e9d5ff; font-size:0.9rem;">Protected patterns detected: <strong>{', '.join(result.privacy.detected_patterns) if result.privacy else 'PII/Tokens'}</strong>. Query quarantined to device execution.</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # 3. Route Badge & Metrics Row
    badge_classes = {
        "LOCAL_SIMPLE": ("badge-glow badge-local-simple", "🟢 LOCAL SLM INFERENCE"),
        "LOCAL_COMMAND": ("badge-glow badge-local-command", "🔵 LOCAL COMMAND DISPATCH"),
        "CLOUD_COMPLEX": ("badge-glow badge-cloud-complex", "🔴 CLOUD MODEL ESCALATION"),
        "AMBIGUOUS": ("badge-glow badge-ambiguous", "🟡 AMBIGUOUS INTENT"),
    }
    b_class, b_label = badge_classes.get(result.final_route, ("badge-glow badge-ambiguous", result.final_route))
    if result.privacy_blocked and result.final_route != "CLOUD_COMPLEX":
        b_label = "🔒 PRIVACY GUARD → " + b_label

    col_b, col_m1, col_m2, col_m3 = st.columns([2.5, 1, 1, 1])
    with col_b:
        st.markdown(f'<div class="{b_class}">{b_label}</div>', unsafe_allow_html=True)
    with col_m1:
        st.markdown(f"""
        <div class="stat-box">
          <div class="stat-box-val">{int(result.confidence * 100)}%</div>
          <div class="stat-box-lbl">Confidence</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"""
        <div class="stat-box">
          <div class="stat-box-val">{result.latency_ms:.0f}<span style="font-size:0.9rem; color:#94a3b8;">ms</span></div>
          <div class="stat-box-lbl">End-to-End Latency</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m3:
        st.markdown(f"""
        <div class="stat-box">
          <div class="stat-box-val">{result.slm_latency_ms:.0f}<span style="font-size:0.9rem; color:#94a3b8;">ms</span></div>
          <div class="stat-box-lbl">SLM Inference</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Response Display & Deep Explainability
    col_response, col_explain = st.columns([1.2, 1])

    with col_response:
        st.markdown('<div class="er-card">', unsafe_allow_html=True)
        st.markdown("""
        <div class="er-card-header">
          <div class="er-card-title">💬 Generated Response</div>
        </div>
        """, unsafe_allow_html=True)

        if result.final_route == "LOCAL_COMMAND" and result.tool_result:
            tr = result.tool_result
            tool_name = tr.get("tool", "unknown")
            msg = tr.get("message", "")
            st.markdown(f"""
            <div style="background:rgba(37,99,235,0.15); border:1px solid rgba(59,130,246,0.4); border-radius:12px; padding:20px;">
              <div style="font-size:0.85rem; color:#93c5fd; text-transform:uppercase; font-weight:700; letter-spacing:1px; margin-bottom:6px;">Smart Home Tool Execution</div>
              <div style="font-size:1.2rem; font-weight:700; color:#eff6ff; margin-bottom:8px;">✅ {msg}</div>
              <div style="font-family:'JetBrains Mono'; font-size:0.82rem; color:#bfdbfe;">
                Tool Dispatched: <code>{tool_name}</code> &nbsp;|&nbsp; Device Status: Synchronized
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            response_text = result.response or "(No response generated)"
            st.markdown(response_text)

        st.markdown("</div>", unsafe_allow_html=True)

    with col_explain:
        st.markdown('<div class="er-card">', unsafe_allow_html=True)
        st.markdown("""
        <div class="er-card-header">
          <div class="er-card-title">🔍 Decision Audit & Signals</div>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["Decision Chain", "Signal Radar", "Neural Classification"])

        with tab1:
            for step in result.reason_chain:
                st.markdown(f"""
                <div class="reason-step">
                  <span style="color:#6366f1; font-size:0.9rem;">✔</span>
                  <span>{step}</span>
                </div>
                """, unsafe_allow_html=True)

        with tab2:
            if result.signals:
                sig = result.signals
                s_cols = st.columns(2)
                with s_cols[0]:
                    st.metric("Words / Length", f"{sig.word_count} words")
                    st.metric("Command Signal", f"{sig.is_command:.2f}")
                    st.metric("Math Signal", f"{sig.is_math:.2f}")
                with s_cols[1]:
                    st.metric("Complexity Score", f"{sig.complexity_score:.2f}")
                    st.metric("Tool / Hardware Signal", f"{sig.is_tool:.2f}")
                    st.metric("Question Signal", f"{sig.is_question:.2f}")

        with tab3:
            if result.slm_classification:
                sc = result.slm_classification
                st.markdown(f"""
                <div style="font-size:0.9rem; line-height:1.6;">
                  <strong>Model Used:</strong> <code>{st.session_state.get('selected_model', OLLAMA_MODEL)}</code><br>
                  <strong>Model Intent:</strong> <em>{sc.intent or 'N/A'}</em><br>
                  <strong>Raw Route:</strong> <code>{sc.route}</code><br>
                  <strong>Model Confidence:</strong> <code>{sc.confidence:.2f}</code><br>
                  <strong>Model Reasoning:</strong> {sc.reason or 'Direct evaluation.'}
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # 5. History Log Table
    if st.session_state["history"]:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📜 Recent Routing History in this Session", expanded=False):
            hist_list = list(st.session_state["history"])
            st.dataframe(
                hist_list,
                use_container_width=True,
                column_config={
                    "query": "Request",
                    "route": "Route Selected",
                    "conf": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1),
                    "latency": "Latency (ms)",
                    "privacy": "Privacy Flag",
                }
            )
