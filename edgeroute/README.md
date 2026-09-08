# EdgeRoute

**Local-First AI Inference Router**

> *Decide locally. Execute locally when possible. Escalate only when necessary.*

---

## Problem

Modern AI applications route every request to large cloud language models.  This creates real problems:

| Issue | Impact |
|-------|--------|
| **Latency** | Round-trip to cloud adds 500–3000ms per request |
| **Privacy** | Sensitive data (PII, credentials) leaves the device |
| **Cost** | Cloud token costs accumulate at scale |
| **Connectivity** | Requires reliable internet connection |
| **Edge/IoT** | Impossible on devices with no cloud access |

Most user requests are *not* complex enough to require a 70B-parameter cloud model.  Asking GPT-4 "What is 2 + 2?" or "Turn on the light" is wasteful, slow, and unnecessary.

---

## Solution: Local-First Routing

EdgeRoute is a **local AI router** that decides where to handle each request *before* sending it anywhere.

- **Simple requests** → answered directly by a small local model (Qwen2.5-0.5B)
- **Commands** → executed by local tool functions (no LLM needed at all)
- **Complex requests** → escalated to a cloud LLM (only when necessary)
- **Sensitive data** → never leaves the device (privacy guard)
- **Ambiguous requests** → handled with a safe deterministic fallback

The classification decision is **always made locally**.  The cloud is **never used for routing**.

---

## Architecture

```
USER REQUEST
      │
      ▼
┌─────────────────────┐
│  Request Preprocessing│  (validate, strip)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Feature Extraction  │  router/signals.py
│  (local, no LLM)    │  word count, command/tool/complexity signals
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Privacy Guard       │  router/privacy.py
│  (local, no LLM)    │  regex scan for PII, API keys, passwords
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Local SLM Router    │  models/slm.py
│  Qwen2.5-0.5B via   │  structured JSON classification
│  Ollama              │  intent, route, confidence, reason
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Policy Engine       │  router/policy.py
│  (deterministic)     │  confidence thresholds, command/privacy/complexity overrides
└──────────┬──────────┘
           │
     ┌─────┴────────────────────────┐
     │              │               │
     ▼              ▼               ▼
LOCAL_SIMPLE  LOCAL_COMMAND   CLOUD_COMPLEX
     │              │               │
     ▼              ▼               ▼
Local SLM      Local Tool      Cloud Adapter
(generate)     (dispatch)      (mock/live)
     │              │               │
     └──────────────┴───────────────┘
                    │
                    ▼
             Final Response
```

### Key architectural principle

The **policy engine** sits between the SLM and the final decision.  It can override the SLM for:

1. Low confidence → deterministic fallback
2. Strong command signals → `LOCAL_COMMAND`
3. Privacy-sensitive data → block cloud escalation
4. High complexity signals → escalate to `CLOUD_COMPLEX`
5. Malformed SLM output → safe fallback

This means the system is **robust even when Ollama is unavailable** — deterministic routing continues to work.

---

## Routing Classes

| Route | Description | Examples |
|-------|-------------|---------|
| `LOCAL_SIMPLE` | Short factual questions, arithmetic, definitions | "What is 2+2?", "Define recursion." |
| `LOCAL_COMMAND` | Device control, tool execution | "Turn on the light.", "Lock the door." |
| `CLOUD_COMPLEX` | Long-form generation, complex analysis, sophisticated coding | "Write a 1500-word story about Mars." |
| `AMBIGUOUS` | Vague or underspecified requests | "Help me.", "Fix it." |

---

## Why Qwen2.5-0.5B-Instruct?

| Property | Value |
|----------|-------|
| **Parameters** | 500 million |
| **VRAM** | ~1 GB (4-bit quantized) |
| **Laptop compatible** | Yes — CPU inference possible |
| **Instruction-tuned** | Yes — follows JSON output format |
| **License** | Apache 2.0 |
| **Edge deployable** | Yes — tested on consumer hardware |

Qwen2.5-0.5B was selected because:
- Small enough to run on a laptop CPU without a GPU
- Instruction-tuned, enabling structured JSON output
- Accurate enough for routing classification (not generation)
- Configurable: any Ollama-compatible model can be substituted via `OLLAMA_MODEL`

---

## Privacy Guard

```
router/privacy.py
```

**Disclaimer: Lightweight local privacy guard for demonstration purposes. Not a production-grade PII detector.**

The privacy guard scans every query *before* cloud routing using local regex patterns:

| Pattern | Example |
|---------|---------|
| Email addresses | `user@example.com` |
| Phone numbers | `+1-555-867-5309` |
| Credit card numbers | `4111 1111 1111 1111` |
| API keys / tokens | `sk-abc123...`, `ghp_...`, `AKIA...` |
| Inline passwords | `password is hunter2` |
| SSN-like numbers | `123-45-6789` |
| Private/secret key mentions | `private key`, `bearer token` |

If sensitive data is detected:
- The request is **never forwarded to the cloud**
- The UI shows: *"🔒 Cloud escalation blocked by local privacy policy"*
- The request is handled locally instead

For production use, integrate a dedicated PII detection library such as Microsoft Presidio or a fine-tuned NER model.

---

## Project Structure

```
edgeroute/
├── app/
│   └── ui.py              # Streamlit demo UI
├── api/
│   └── main.py            # FastAPI backend
├── router/
│   ├── classifier.py      # Main routing pipeline orchestrator
│   ├── policy.py          # Deterministic policy / safety engine
│   ├── signals.py         # Local feature extraction (no LLM)
│   └── privacy.py         # Local privacy guard (no LLM)
├── models/
│   └── slm.py             # LocalSLM abstraction (Ollama/Qwen)
├── tools/
│   └── local_tools.py     # Safe simulated local tool implementations
├── cloud/
│   └── adapter.py         # Optional cloud LLM adapter
├── evaluation/
│   ├── test_cases.json    # 60 diverse test cases
│   ├── evaluate.py        # Full evaluation metrics
│   └── benchmark.py       # Latency / resource benchmarks
├── tests/
│   ├── test_classifier.py # Integration tests (mock SLM)
│   ├── test_policy.py     # Policy engine unit tests
│   ├── test_privacy.py    # Privacy guard unit tests
│   └── test_tools.py      # Local tool unit tests
├── config.py              # Configuration (env vars)
├── main.py                # CLI entrypoint
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| SLM inference | Ollama + Qwen2.5-0.5B-Instruct |
| Feature extraction | Pure Python regex (local, no LLM) |
| Privacy guard | Pure Python regex (local, no LLM) |
| Policy engine | Deterministic Python logic |
| Local tools | Simulated Python functions |
| Cloud adapter | HTTP (OpenAI-compatible), mock mode available |
| API backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Configuration | python-dotenv |
| Evaluation metrics | scikit-learn |
| Benchmarking | psutil |
| Testing | pytest |

---

## Installation

### Prerequisites

- Python 3.13+
- [Ollama](https://ollama.com/download) installed and running

### 1. Clone the repository

```bash
git clone <repo-url>
cd "Edge Route/edgeroute"
```

### 2. Install Python dependencies

```bash
py -m pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env
# Edit .env if needed (defaults work for local development)
```

### 4. Set up Ollama

Start the Ollama application (Windows system tray icon, or):

```bash
# Pull the model (one-time, ~400MB download)
ollama pull qwen2.5:0.5b

# Verify it's working
ollama run qwen2.5:0.5b "Hello"
```

> **Note**: If Ollama is unavailable, EdgeRoute falls back to deterministic routing using extracted signals. All features except live SLM inference continue to work.

---

## Running the Application

All commands are run from the `edgeroute/` directory.

### CLI (quickest start)

```bash
# Interactive mode
py main.py

# Single query
py main.py "What is 2 + 2?"
py main.py "Turn on the bedroom light."
py main.py "Write a 1500-word story about Mars."

# JSON output
py main.py --json "Define recursion."

# Health check
py main.py --check
```

### Streamlit UI

```bash
py -m streamlit run app/ui.py
# Opens at http://localhost:8501
```

### FastAPI Backend

```bash
py -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
# API docs at http://localhost:8000/docs
```

#### API endpoints

```bash
# Route a query
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"query": "What is 2 + 2?"}'

# Health check
curl http://localhost:8000/health

# Telemetry
curl http://localhost:8000/telemetry
```

### Run Tests

```bash
py -m pytest tests/ -v
# Expected: 60 passed
```

### Run Evaluation

```bash
# Full evaluation (requires Ollama for best accuracy)
py evaluation/evaluate.py

# With verbose per-case output
py evaluation/evaluate.py --verbose

# Save results
py evaluation/evaluate.py --output results.json
```

### Run Benchmark

```bash
py evaluation/benchmark.py

# With more SLM iterations
py evaluation/benchmark.py --iterations 10

# Save benchmark results
py evaluation/benchmark.py --output benchmark_results.json
```

---

## Demo Scenarios

### Scenario 1 — Simple factual question

```
Input: "What is 2 + 2?"
Route: 🟢 LOCAL_SIMPLE
Response: (generated by local Qwen2.5-0.5B)
Latency: depends on hardware
```

### Scenario 2 — Local device command

```
Input: "Turn on the bedroom light."
Route: 🔵 LOCAL_COMMAND
Tool: turn_on_light
Status: SUCCESS
Message: "Light turned ON in the bedroom." [Simulated]
```

### Scenario 3 — Complex generation

```
Input: "Write a 1500-word story about a dragon living on Mars."
Route: 🔴 CLOUD_COMPLEX
Response: [mock cloud response unless MOCK_CLOUD=false and API key set]
```

### Scenario 4 — Privacy protection

```
Input: "My email is user@example.com. Please summarize my account."
Route: 🔒 BLOCKED → LOCAL_SIMPLE
Reason: email_address pattern detected
Cloud escalation: BLOCKED
```

### Scenario 5 — Ambiguous request

```
Input: "Help me with my project."
Route: 🟡 AMBIGUOUS
Response: "I'm not sure how to handle this request. Could you provide more context?"
```

---

## Routing Logic

The routing pipeline runs in this order:

1. **Signal extraction** — extract word count, command/tool/complexity/math signals deterministically
2. **Privacy scan** — check for PII, credentials, API keys
3. **SLM classification** — ask local Qwen2.5-0.5B to classify and explain in JSON
4. **Policy evaluation** — apply hard rules to validate/override SLM result:
   - Confidence < threshold → deterministic fallback
   - Command verb + tool keyword → `LOCAL_COMMAND`
   - Sensitive data detected → block `CLOUD_COMPLEX`
   - High complexity score → `CLOUD_COMPLEX`
5. **Response generation** — execute the chosen route

---

## Explainability

Every routing decision includes a full reason chain. Example:

```
Route: LOCAL_COMMAND
Confidence: 92%

Reason chain:
  • Extracted signals: 5 words, complexity=0.00, command=0.60, tool=0.50.
  • Privacy guard: no sensitive data detected.
  • SLM classified: LOCAL_COMMAND (confidence=0.92, reason='Device control command').
  • Command intent confirmed by signal extraction.
  • Executed local tool: turn_on_light.
```

---

## Configuration Reference

All settings in `.env`:

```env
OLLAMA_HOST=http://localhost:11434     # Ollama server URL
OLLAMA_MODEL=qwen2.5:0.5b             # Model name (change freely)
OLLAMA_TIMEOUT=60                      # Inference timeout (seconds)
SLM_CONFIDENCE_THRESHOLD=0.70         # Min confidence to trust SLM
COMPLEXITY_THRESHOLD=0.70             # Complexity score to trigger escalation
COMPLEXITY_WORD_THRESHOLD=60          # Word count to trigger escalation
MOCK_CLOUD=true                        # Use mock cloud response (no API key needed)
CLOUD_API_KEY=                         # Optional: OpenAI-compatible API key
CLOUD_MODEL=gpt-4o-mini               # Cloud model name
CLOUD_API_BASE=https://api.openai.com/v1  # Cloud API base URL
```

**To use a different local model**, change `OLLAMA_MODEL`:
```env
OLLAMA_MODEL=llama3.2:1b
```

---

## Evaluation Dataset

`evaluation/test_cases.json` contains 60 diverse test cases:

| Category | Count | Description |
|----------|-------|-------------|
| `LOCAL_SIMPLE` | 15 | Factual questions, arithmetic, definitions, conversions |
| `LOCAL_COMMAND` | 15 | IoT device control commands |
| `CLOUD_COMPLEX` | 15 | Long-form generation, system design, complex analysis |
| `AMBIGUOUS` | 10 | Vague, underspecified requests |
| Privacy/edge | 5 | Queries with PII (expected → `LOCAL_SIMPLE` after blocking) |

Queries are varied: not all are obvious or easy for the router.

---

## Benchmarking

The benchmark script (`evaluation/benchmark.py`) measures:

- **Signal extraction latency** — deterministic, typically sub-millisecond
- **Privacy check latency** — deterministic, typically sub-millisecond
- **SLM cold-start latency** — first inference after model load (longer)
- **SLM warm latency** — subsequent inferences (faster)
- **Full pipeline latency** — end-to-end including all components
- **Memory usage** — RSS before and after benchmark

> **Note**: All numbers are measured from the actual machine at benchmark time. No values are fabricated. Latency depends heavily on hardware (CPU, RAM, whether GPU is present). Results will differ across machines.

---

## Limitations

| Limitation | Details |
|------------|---------|
| **Lightweight complexity estimation** | The complexity signal uses heuristic regex patterns, not semantic understanding |
| **Small model capability** | Qwen2.5-0.5B may misclassify edge cases; the policy layer compensates |
| **Heuristic privacy detection** | Regex-based — will miss obfuscated PII; not suitable for production PII detection |
| **Simulated tools** | Local tools are simulated; no real hardware is controlled |
| **Cloud adapter** | Requires CLOUD_API_KEY and MOCK_CLOUD=false for live cloud inference |
| **Benchmark hardware-dependent** | All latency numbers are machine-specific |
| **No GPU acceleration assumed** | Designed for CPU inference; GPU would significantly improve SLM speed |
| **Raspberry Pi** | Designed for edge deployment; Raspberry Pi benchmark not performed (hardware unavailable) |

---

## Future Work

| Enhancement | Description |
|-------------|-------------|
| **Learned routing model** | Train a small classifier on routing decisions instead of relying on the SLM |
| **Quantization** | Use GGUF Q4_K_M quantization for faster CPU inference |
| **Raspberry Pi deployment** | Profile and optimize for ARM edge hardware |
| **Adaptive routing** | Track which routes produce good outcomes and adjust thresholds dynamically |
| **Energy-aware routing** | Prefer local routes when battery is low |
| **Token/cost estimation** | Estimate cloud token cost before escalating |
| **Personalized routing policies** | Per-user confidence thresholds and privacy preferences |
| **Production PII detection** | Integrate Microsoft Presidio or a fine-tuned NER model |
| **Streaming responses** | Stream SLM output tokens for better perceived latency |
| **Context management** | Multi-turn conversation routing |

---

## Security Notes

- API keys are **never hard-coded** — use environment variables only
- Local tools use an **explicit allowlist** — arbitrary tool names are rejected
- No **shell commands** are executed based on user input
- Secrets are **never logged**
- The cloud adapter is **never called during classification**
- Privacy guard runs **before** any cloud routing decision

---

*EdgeRoute — Local-First AI Inference Router*
*Built to demonstrate: SLMs, local inference, AI routing, edge AI, privacy-aware systems, and deterministic safety policies.*
