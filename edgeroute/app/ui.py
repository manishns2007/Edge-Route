"""
app/ui.py
=========
EdgeRoute — Streamlit Demo UI

Run from the edgeroute/ directory:
  py -m streamlit run app/ui.py

Features:
  - Request routing with one click
  - Visual route badge (LOCAL_SIMPLE / LOCAL_COMMAND / CLOUD_COMPLEX / AMBIGUOUS)
  - Full explainability panel (signals, privacy, SLM result, policy chain)
  - In-session telemetry dashboard
  - Request history table
  - Privacy violation alerts
  - Tool execution results
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
    page_title="EdgeRoute — Local-First AI Router",
    page_icon="🔀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS for a premium, dark-mode design
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* === Import === */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* === Global === */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* === Dark background === */
.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1321 50%, #0a0e1a 100%);
    color: #e2e8f0;
}

/* === Header === */
.er-header {
    background: linear-gradient(90deg, #1e40af 0%, #7c3aed 50%, #db2777 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(124,58,237,0.3);
}
.er-header h1 { font-size: 2.2rem; font-weight: 700; color: white; margin: 0; letter-spacing: -0.5px; }
.er-header p  { color: rgba(255,255,255,0.85); margin: 4px 0 0; font-size: 1rem; }

/* === Route badges === */
.badge {
    display: inline-block;
    padding: 10px 20px;
    border-radius: 50px;
    font-weight: 700;
    font-size: 1.1rem;
    letter-spacing: 0.5px;
    text-align: center;
    width: 100%;
}
.badge-local   { background: linear-gradient(135deg, #065f46, #059669); color: #d1fae5; box-shadow: 0 4px 16px rgba(5,150,105,0.4); }
.badge-command { background: linear-gradient(135deg, #1e3a5f, #2563eb); color: #bfdbfe; box-shadow: 0 4px 16px rgba(37,99,235,0.4); }
.badge-cloud   { background: linear-gradient(135deg, #7f1d1d, #dc2626); color: #fecaca; box-shadow: 0 4px 16px rgba(220,38,38,0.4); }
.badge-ambig   { background: linear-gradient(135deg, #4a2c00, #d97706); color: #fef3c7; box-shadow: 0 4px 16px rgba(217,119,6,0.4); }
.badge-privacy { background: linear-gradient(135deg, #4a004a, #9333ea); color: #f3e8ff; box-shadow: 0 4px 16px rgba(147,51,234,0.4); }

/* === Cards === */
.er-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    backdrop-filter: blur(8px);
}
.er-card h4 { color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 12px; }

/* === Confidence bar === */
.conf-bar-bg {
    background: rgba(255,255,255,0.1);
    border-radius: 50px;
    height: 8px;
    overflow: hidden;
    margin: 4px 0 12px;
}
.conf-bar-fill {
    height: 100%;
    border-radius: 50px;
    background: linear-gradient(90deg, #3b82f6, #8b5cf6);
    transition: width 0.6s ease;
}

/* === Metric box === */
.metric-box {
    background: rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.08);
}
.metric-box .metric-val { font-size: 1.8rem; font-weight: 700; color: #a78bfa; }
.metric-box .metric-lbl { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }

/* === Reason chain item === */
.reason-item {
    background: rgba(255,255,255,0.03);
    border-left: 3px solid #4f46e5;
    border-radius: 0 8px 8px 0;
    padding: 8px 14px;
    margin: 6px 0;
    font-size: 0.88rem;
    color: #cbd5e1;
}

/* === Signal pill === */
.sig-pill {
    display: inline-block;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.35);
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78rem;
    color: #a5b4fc;
    margin: 3px;
}
.sig-pill-active {
    background: rgba(99,102,241,0.35);
    border-color: rgba(99,102,241,0.7);
    color: #c7d2fe;
    font-weight: 600;
}

/* === Privacy alert === */
.privacy-alert {
    background: linear-gradient(135deg, rgba(147,51,234,0.15), rgba(219,39,119,0.1));
    border: 1px solid rgba(147,51,234,0.4);
    border-radius: 12px;
    padding: 16px 20px;
    color: #e9d5ff;
}

/* === Tool result === */
.tool-result {
    background: rgba(37,99,235,0.12);
    border: 1px solid rgba(37,99,235,0.3);
    border-radius: 10px;
    padding: 14px 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #bfdbfe;
}

/* === History row === */
.hist-row {
    background: rgba(255,255,255,0.025);
    border-radius: 8px;
    padding: 8px 14px;
    margin: 4px 0;
    font-size: 0.85rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid rgba(255,255,255,0.05);
}

/* === Sidebar === */
section[data-testid="stSidebar"] {
    background: rgba(15,23,42,0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}

/* === Override Streamlit defaults === */
.stTextArea textarea {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
}
.stButton > button {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 12px 28px !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(79,70,229,0.5) !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state initialisation
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
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="er-header">
  <h1>🔀 EdgeRoute</h1>
  <p>Local-First AI Inference Router &nbsp;·&nbsp; Decide locally. Execute locally when possible. Escalate only when necessary.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — Model info & quick stats
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    from config import OLLAMA_HOST, OLLAMA_MODEL, MOCK_CLOUD, SLM_CONFIDENCE_THRESHOLD
    st.markdown(f"""
    <div class="er-card">
      <h4>Ollama</h4>
      <div style="font-size:0.85rem; color:#94a3b8;">
        Host: <code style="color:#a5b4fc">{OLLAMA_HOST}</code><br>
        Model: <code style="color:#a5b4fc">{OLLAMA_MODEL}</code>
      </div>
    </div>
    <div class="er-card">
      <h4>Policy</h4>
      <div style="font-size:0.85rem; color:#94a3b8;">
        Confidence threshold: <code style="color:#a5b4fc">{SLM_CONFIDENCE_THRESHOLD}</code><br>
        Cloud mode: <code style="color:#a5b4fc">{'MOCK' if MOCK_CLOUD else 'LIVE'}</code>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🧪 Quick Test Queries")
    EXAMPLES = [
        ("🔢 Simple", "What is 2 + 2?"),
        ("💡 Command", "Turn on the bedroom light."),
        ("🌡️ Command", "Set the temperature to 22 degrees."),
        ("🔒 Command", "Lock the front door."),
        ("☁️ Complex", "Write a 1500-word story about a dragon living on Mars."),
        ("🧠 Complex", "Design a scalable distributed payment system."),
        ("🔐 Privacy", "My email is user@example.com, please summarize."),
        ("❓ Ambiguous", "Help me with my project."),
    ]
    for label, query in EXAMPLES:
        if st.button(label, key=f"ex_{label}"):
            st.session_state["main_input"] = query
            st.session_state["auto_route"] = True
            st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Session Stats")
    total = st.session_state["total_requests"]
    if total > 0:
        avg_lat = st.session_state["total_latency_ms"] / total
        st.metric("Total requests", total)
        st.metric("Avg latency", f"{avg_lat:.0f} ms")
        st.metric("Privacy blocked", st.session_state["privacy_blocked"])
    else:
        st.caption("No requests yet.")

# ---------------------------------------------------------------------------
# Main input area
# ---------------------------------------------------------------------------

col_input, col_spacer = st.columns([3, 1])
with col_input:
    user_query = st.text_area(
        "Enter your request",
        height=100,
        placeholder="What is 2 + 2?   |   Turn on the light.   |   Write a 1500-word story ...",
        key="main_input",
        label_visibility="collapsed",
    )
    route_btn = st.button("🔀 Route Request", use_container_width=True)

# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------

ROUTE_BADGE_MAP = {
    "LOCAL_SIMPLE": ("badge badge-local",   "🟢 LOCAL SLM"),
    "LOCAL_COMMAND": ("badge badge-command", "🔵 LOCAL COMMAND"),
    "CLOUD_COMPLEX": ("badge badge-cloud",   "🔴 CLOUD ESCALATION"),
    "AMBIGUOUS":     ("badge badge-ambig",   "🟡 AMBIGUOUS"),
}

should_route = route_btn or st.session_state.pop("auto_route", False)

if should_route:
    query_to_route = st.session_state.get("main_input", "").strip()
    if not query_to_route:
        st.warning("Please enter a request first.")
    else:
        with st.spinner("Routing..."):
            from router.classifier import route as classifier_route
            result = classifier_route(query_to_route)

        # Update session state
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
# Result display
# ---------------------------------------------------------------------------

if st.session_state.get("last_result"):
    query_display, result = st.session_state["last_result"]

    st.markdown("---")

    # Privacy alert (top priority)
    if result.privacy_blocked:
        st.markdown("""
        <div class="privacy-alert">
          🔒 <strong>Cloud Escalation Blocked by Local Privacy Policy</strong><br>
          Sensitive information was detected in this request. The query will NOT be forwarded to any cloud service.
        </div>
        """, unsafe_allow_html=True)

    # Route badge + confidence + latency
    badge_class, badge_label = ROUTE_BADGE_MAP.get(
        result.final_route, ("badge badge-ambig", "❓ UNKNOWN")
    )
    if result.privacy_blocked and result.final_route != "CLOUD_COMPLEX":
        badge_label = "🔒 PRIVACY BLOCKED → " + badge_label

    col_badge, col_conf, col_lat = st.columns([2, 1, 1])
    with col_badge:
        st.markdown(f'<div class="{badge_class}">{badge_label}</div>', unsafe_allow_html=True)
    with col_conf:
        conf_pct = int(result.confidence * 100)
        st.markdown(f"""
        <div class="metric-box">
          <div class="metric-val">{conf_pct}%</div>
          <div class="metric-lbl">Confidence</div>
        </div>
        """, unsafe_allow_html=True)
    with col_lat:
        st.markdown(f"""
        <div class="metric-box">
          <div class="metric-val">{result.latency_ms:.0f}</div>
          <div class="metric-lbl">Latency (ms)</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main content columns
    col_resp, col_explain = st.columns([1, 1])

    # --- Response column ---
    with col_resp:
        st.markdown('<div class="er-card"><h4>📨 Response</h4>', unsafe_allow_html=True)

        if result.final_route == "LOCAL_COMMAND" and result.tool_result:
            tr = result.tool_result
            status_icon = "✅" if tr.get("status") == "success" else "⚠️"
            st.markdown(f"""
            <div class="tool-result">
              {status_icon} <strong>Tool:</strong> {tr.get('tool', 'unknown')}<br>
              <strong>Status:</strong> {tr.get('status', '?').upper()}<br>
              <strong>Message:</strong> {tr.get('message', '')}<br>
              <em style="color:#64748b; font-size:0.78rem;">[Simulated execution]</em>
            </div>
            """, unsafe_allow_html=True)
        else:
            response_text = result.response or "(No response)"
            st.markdown(
                f'<div style="color:#e2e8f0; font-size:0.95rem; line-height:1.6">{response_text}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        # SLM status
        if not result.ollama_available:
            st.markdown("""
            <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:8px;padding:10px 14px;color:#fca5a5;font-size:0.82rem;">
              ⚠️ Ollama is not running. Using deterministic fallback routing.<br>
              Start Ollama and pull <code>qwen2.5:0.5b</code> for live SLM inference.
            </div>
            """, unsafe_allow_html=True)

    # --- Explainability column ---
    with col_explain:
        st.markdown('<div class="er-card"><h4>🔍 Explainability</h4>', unsafe_allow_html=True)

        # SLM classification
        slm_cls = result.slm_classification
        if slm_cls and not slm_cls.error:
            st.markdown(f"""
            <div style="margin-bottom:12px;">
              <div style="color:#64748b;font-size:0.72rem;text-transform:uppercase;letter-spacing:1px;">SLM Classification</div>
              <div style="color:#a78bfa;font-weight:600;">{slm_cls.route}</div>
              <div style="color:#94a3b8;font-size:0.82rem;">{slm_cls.reason}</div>
              <div class="conf-bar-bg"><div class="conf-bar-fill" style="width:{int(slm_cls.confidence*100)}%"></div></div>
            </div>
            """, unsafe_allow_html=True)
        elif slm_cls and slm_cls.error:
            st.markdown(f'<div style="color:#f87171;font-size:0.82rem;">SLM error: {slm_cls.error}</div>', unsafe_allow_html=True)

        # Policy decision
        if result.policy and result.policy.overridden:
            st.markdown(f"""
            <div style="margin-bottom:12px;background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.2);border-radius:8px;padding:10px;">
              <div style="color:#fbbf24;font-size:0.78rem;font-weight:600;">⚡ Policy Override: {result.policy.override_reason}</div>
              <div style="color:#94a3b8;font-size:0.82rem;">Final route adjusted to <strong style="color:#e2e8f0;">{result.policy.final_route}</strong></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Reason chain
    st.markdown('<div class="er-card"><h4>🧠 Reason Chain</h4>', unsafe_allow_html=True)
    for step in result.reason_chain:
        st.markdown(f'<div class="reason-item">{step}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Signals + Privacy side by side
    col_sig, col_priv = st.columns([1, 1])

    with col_sig:
        st.markdown('<div class="er-card"><h4>📡 Extracted Signals</h4>', unsafe_allow_html=True)
        if result.signals:
            s = result.signals
            def _pill(label: str, value: float) -> str:
                active = "sig-pill-active" if value > 0.4 else "sig-pill"
                val_str = f"{value:.2f}" if value not in (0.0, 1.0) else ("✓" if value == 1.0 else "✗")
                return f'<span class="{active}">{label}: {val_str}</span>'

            pills = "".join([
                _pill("Words", float(s.word_count) / 100),  # normalise for display
                _pill("Question", s.is_question),
                _pill("Command", s.is_command),
                _pill("Tool", s.is_tool),
                _pill("Code", s.is_code_request),
                _pill("Reasoning", s.is_reasoning),
                _pill("Creative", s.is_creative),
                _pill("Math", s.is_math),
                _pill("Sensitive", s.is_sensitive),
                _pill("Ambiguous", s.is_ambiguous),
                _pill("Long output", s.expects_long_output),
            ])
            st.markdown(
                f'<div style="margin-top:4px;">{pills}</div>'
                f'<div style="margin-top:10px;color:#64748b;font-size:0.78rem;">Words: {s.word_count} | Chars: {s.char_count} | Complexity: {s.complexity_score:.2f}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_priv:
        st.markdown('<div class="er-card"><h4>🔐 Privacy Guard</h4>', unsafe_allow_html=True)
        if result.privacy:
            p = result.privacy
            if p.is_sensitive:
                patterns_html = "".join(
                    f'<span class="sig-pill-active" style="background:rgba(147,51,234,0.3);border-color:rgba(147,51,234,0.6);color:#d8b4fe;">{pat}</span>'
                    for pat in p.detected_patterns
                )
                st.markdown(
                    f'<div style="color:#d8b4fe;font-weight:600;margin-bottom:8px;">⚠️ Sensitive data detected</div>'
                    f'<div>{patterns_html}</div>'
                    f'<div style="color:#94a3b8;font-size:0.78rem;margin-top:10px;">{p.blocked_reason[:120]}...</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="color:#4ade80;font-weight:600;">✅ No sensitive data detected</div>'
                    '<div style="color:#64748b;font-size:0.82rem;margin-top:6px;">Safe for all routing destinations.</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Telemetry Dashboard
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown("### 📊 Routing Telemetry")

counter = st.session_state["route_counter"]
total = st.session_state["total_requests"]

col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)
metrics_data = [
    (col_t1, "Total", total, "#a78bfa"),
    (col_t2, "Local SLM", counter.get("LOCAL_SIMPLE", 0), "#4ade80"),
    (col_t3, "Commands", counter.get("LOCAL_COMMAND", 0), "#60a5fa"),
    (col_t4, "Cloud", counter.get("CLOUD_COMPLEX", 0), "#f87171"),
    (col_t5, "Privacy Blocked", st.session_state["privacy_blocked"], "#c084fc"),
]
for col, label, value, color in metrics_data:
    with col:
        pct = (value / total * 100) if total > 0 else 0
        st.markdown(f"""
        <div class="metric-box">
          <div class="metric-val" style="color:{color}">{value}</div>
          <div class="metric-lbl">{label}</div>
          <div style="color:#64748b;font-size:0.7rem;margin-top:4px;">{pct:.0f}% of total</div>
        </div>
        """, unsafe_allow_html=True)

# Route distribution bar
if total > 0:
    st.markdown("<br>", unsafe_allow_html=True)
    route_colors = {
        "LOCAL_SIMPLE": "#4ade80",
        "LOCAL_COMMAND": "#60a5fa",
        "CLOUD_COMPLEX": "#f87171",
        "AMBIGUOUS": "#facc15",
    }
    bar_segments = ""
    for route_name, color in route_colors.items():
        cnt = counter.get(route_name, 0)
        if cnt > 0:
            pct = cnt / total * 100
            bar_segments += f'<div style="width:{pct:.1f}%;background:{color};height:100%;display:inline-block;"></div>'

    avg_lat = st.session_state["total_latency_ms"] / total if total > 0 else 0
    st.markdown(f"""
    <div class="er-card">
      <h4>Route Distribution</h4>
      <div style="background:rgba(255,255,255,0.08);border-radius:6px;height:16px;overflow:hidden;margin-bottom:12px;">
        {bar_segments}
      </div>
      <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:0.82rem;color:#94a3b8;">
        <span>🟢 Local SLM: {counter.get('LOCAL_SIMPLE',0)}</span>
        <span>🔵 Commands: {counter.get('LOCAL_COMMAND',0)}</span>
        <span>🔴 Cloud: {counter.get('CLOUD_COMPLEX',0)}</span>
        <span>🟡 Ambiguous: {counter.get('AMBIGUOUS',0)}</span>
        <span style="margin-left:auto;color:#a78bfa;">Avg latency: {avg_lat:.0f}ms</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

if st.session_state["history"]:
    st.markdown("### 🕒 Request History")
    st.markdown('<div class="er-card"><h4>Recent Requests</h4>', unsafe_allow_html=True)

    route_icons = {
        "LOCAL_SIMPLE": "🟢",
        "LOCAL_COMMAND": "🔵",
        "CLOUD_COMPLEX": "🔴",
        "AMBIGUOUS": "🟡",
    }
    for h in list(st.session_state["history"])[:15]:
        icon = route_icons.get(h["route"], "❓")
        priv_badge = " 🔒" if h["privacy"] else ""
        st.markdown(f"""
        <div class="hist-row">
          <span style="color:#e2e8f0;">{icon} {h['query']}{priv_badge}</span>
          <span style="color:#64748b;font-size:0.78rem;white-space:nowrap;margin-left:12px;">
            {h['route']} · {h['conf']*100:.0f}% · {h['latency']:.0f}ms
          </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("""
<div style="text-align:center;color:#334155;font-size:0.75rem;margin-top:40px;padding:20px;">
  EdgeRoute · Local-First AI Inference Router · Classification always runs locally · Cloud is optional
</div>
""", unsafe_allow_html=True)
