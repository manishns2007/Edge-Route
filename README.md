# EdgeRoute

### Local-First AI Inference Router

> **Decide locally. Execute locally when possible. Escalate only when necessary.**

EdgeRoute is a **local-first AI inference router** that determines how a user request should be handled before sending it anywhere.

Instead of forwarding every request to an expensive cloud LLM, EdgeRoute combines a **small local language model, deterministic signals, privacy checks, and a policy engine** to decide whether a request should:

* 🟢 Stay local
* 🔵 Execute through a local tool
* 🔴 Escalate to a cloud LLM
* 🟡 Fall back safely when the request is ambiguous

The routing decision itself is always performed locally.

---

## Why EdgeRoute?

Modern AI applications often send every request directly to a cloud model. That approach introduces several problems:

| Problem             | Impact                                                           |
| ------------------- | ---------------------------------------------------------------- |
| **Latency**         | Network round-trips increase response time                       |
| **Privacy**         | Sensitive information may leave the device                       |
| **Cost**            | Every cloud request consumes tokens                              |
| **Connectivity**    | Cloud inference requires an internet connection                  |
| **Edge deployment** | Cloud-only architectures are unsuitable for disconnected devices |

Many requests simply do not require a large cloud model.

> Asking a cloud LLM *"What is 2 + 2?"* or *"Turn on the light"* is unnecessary when the request can be handled locally.

EdgeRoute addresses this by putting an intelligent routing layer **before inference**.

---

# Architecture

```text
                         USER REQUEST
                              │
                              ▼
                   ┌─────────────────────┐
                   │ Request Preprocessing│
                   │   Validate / Strip  │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │   Signal Extraction │
                   │                     │
                   │ • Word count        │
                   │ • Command signals   │
                   │ • Tool signals      │
                   │ • Complexity        │
                   │ • Math signals      │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │    Privacy Guard    │
                   │                     │
                   │ • PII              │
                   │ • API keys         │
                   │ • Passwords        │
                   │ • Tokens           │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │    Local SLM        │
                   │                     │
                   │ Qwen2.5-0.5B        │
                   │ via Ollama           │
                   │                     │
                   │ Intent              │
                   │ Route               │
                   │ Confidence          │
                   │ Reason              │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │    Policy Engine    │
                   │                     │
                   │ Deterministic rules │
                   │ + safety overrides  │
                   └──────────┬──────────┘
                              │
              ┌───────────────┼────────────────┐
              │               │                │
              ▼               ▼                ▼
       LOCAL_SIMPLE    LOCAL_COMMAND    CLOUD_COMPLEX
              │               │                │
              ▼               ▼                ▼
         Local SLM       Local Tool      Cloud Adapter
         Generation       Execution       Mock / Live
              │               │                │
              └───────────────┴────────────────┘
                              │
                              ▼
                       FINAL RESPONSE
```

### Core design principle

The **local SLM does not have absolute authority** over the routing decision.

The policy engine validates and can override the model's decision when necessary.

For example:

1. Low SLM confidence → deterministic fallback
2. Strong command signals → force `LOCAL_COMMAND`
3. Sensitive information → prevent cloud escalation
4. High complexity → escalate to `CLOUD_COMPLEX`
5. Invalid SLM output → safe fallback

This gives EdgeRoute a **defense-in-depth routing architecture** rather than relying entirely on a language model.

---

# Routing Classes

| Route              | Purpose                                     | Example                               |
| ------------------ | ------------------------------------------- | ------------------------------------- |
| 🟢 `LOCAL_SIMPLE`  | Simple questions and lightweight generation | `What is 2 + 2?`                      |
| 🔵 `LOCAL_COMMAND` | Local device/tool actions                   | `Turn on the bedroom light.`          |
| 🔴 `CLOUD_COMPLEX` | Complex reasoning and long-form generation  | `Write a 1500-word story about Mars.` |
| 🟡 `AMBIGUOUS`     | Vague or underspecified requests            | `Help me with this.`                  |

---

# Local Model

EdgeRoute uses **Qwen2.5-0.5B-Instruct through Ollama** as its default local routing model.

The model is not primarily being used as a general-purpose chatbot. Its main responsibility is to **classify the request and produce structured routing information**.

### Why a small model?

A routing model does not need the same capabilities as a large generative model.

The smaller model provides:

* Low resource requirements
* Local inference
* CPU compatibility
* Structured classification
* No cloud dependency for routing
* The ability to run on consumer hardware

The model can also be replaced through configuration:

```env
OLLAMA_MODEL=qwen2.5:0.5b
```

For example:

```env
OLLAMA_MODEL=llama3.2:1b
```

---

# Privacy Guard

EdgeRoute performs a **local privacy scan before cloud escalation**.

The privacy guard currently uses lightweight regular-expression detection for patterns such as:

| Pattern           | Example                        |
| ----------------- | ------------------------------ |
| Email             | `user@example.com`             |
| Phone number      | `+1-555-867-5309`              |
| Credit card       | `4111 1111 1111 1111`          |
| API keys          | `sk-...`, `ghp_...`, `AKIA...` |
| Passwords         | `password is hunter2`          |
| SSN-like values   | `123-45-6789`                  |
| Secret references | `private key`, `bearer token`  |

When sensitive information is detected:

```text
User Request
     │
     ▼
Privacy Guard
     │
     ├── Sensitive → Block cloud escalation
     │
     └── Safe → Continue routing
```

The request can then be handled locally instead.

> **Important:** The current privacy guard is a lightweight demonstration mechanism, not a production-grade PII detection system. Production deployments should use a dedicated PII detection solution such as Microsoft Presidio or a suitable NER-based system.

---

# Project Structure

```text
edgeroute/
│
├── app/
│   └── ui.py
│       └── Streamlit demonstration UI
│
├── api/
│   └── main.py
│       └── FastAPI backend
│
├── router/
│   ├── classifier.py
│   │   └── Main routing pipeline
│   ├── policy.py
│   │   └── Deterministic policy engine
│   ├── signals.py
│   │   └── Local feature extraction
│   └── privacy.py
│       └── Local privacy detection
│
├── models/
│   └── slm.py
│       └── Local SLM / Ollama integration
│
├── tools/
│   └── local_tools.py
│       └── Allowlisted simulated local tools
│
├── cloud/
│   └── adapter.py
│       └── Optional cloud LLM adapter
│
├── evaluation/
│   ├── test_cases.json
│   │   └── Evaluation dataset
│   ├── evaluate.py
│   │   └── Routing evaluation
│   └── benchmark.py
│       └── Latency/resource benchmarking
│
├── tests/
│   ├── test_classifier.py
│   ├── test_policy.py
│   ├── test_privacy.py
│   └── test_tools.py
│
├── config.py
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

# Technology Stack

| Layer             | Technology                     |
| ----------------- | ------------------------------ |
| Local SLM         | Ollama + Qwen2.5-0.5B-Instruct |
| Routing           | Python                         |
| Signal extraction | Python / Regex                 |
| Privacy detection | Python / Regex                 |
| Policy engine     | Deterministic Python           |
| Local tools       | Python                         |
| Cloud adapter     | OpenAI-compatible HTTP API     |
| Backend           | FastAPI + Uvicorn              |
| UI                | Streamlit                      |
| Configuration     | python-dotenv                  |
| Evaluation        | scikit-learn                   |
| Benchmarking      | psutil                         |
| Testing           | pytest                         |

---

# Getting Started

## Prerequisites

* Python 3.13+
* Ollama
* Git

Install Ollama from:

https://ollama.com/download

---

## 1. Clone the repository

```bash
git clone https://github.com/manishns2007/Edge-Route.git
cd Edge-Route/edgeroute
```

---

## 2. Install dependencies

```bash
py -m pip install -r requirements.txt
```

---

## 3. Configure environment variables

Create the `.env` file:

### Windows

```powershell
copy .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

The default configuration is suitable for local development.

---

## 4. Start Ollama

Pull the default routing model:

```bash
ollama pull qwen2.5:0.5b
```

Verify the model:

```bash
ollama run qwen2.5:0.5b "Hello"
```

If Ollama is unavailable, EdgeRoute can still fall back to deterministic routing using locally extracted signals.

---

# Running EdgeRoute

All commands below should be executed from the `edgeroute/` directory.

## CLI

### Interactive mode

```bash
py main.py
```

### Single request

```bash
py main.py "What is 2 + 2?"
```

```bash
py main.py "Turn on the bedroom light."
```

```bash
py main.py "Write a 1500-word story about Mars."
```

### JSON output

```bash
py main.py --json "Define recursion."
```

### Health check

```bash
py main.py --check
```

---

# Streamlit UI

Start the web interface:

```bash
py -m streamlit run app/ui.py
```

The application will be available locally at:

```text
http://localhost:8501
```

---

# FastAPI Backend

Start the API server:

```bash
py -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

API documentation:

```text
http://localhost:8000/docs
```

### Route a request

```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"What is 2 + 2?\"}"
```

### Health check

```bash
curl http://localhost:8000/health
```

### Telemetry

```bash
curl http://localhost:8000/telemetry
```

---

# Testing

Run the complete test suite:

```bash
py -m pytest tests/ -v
```

The repository includes tests for:

* Routing/classification
* Policy decisions
* Privacy detection
* Local tool execution

---

# Evaluation

EdgeRoute includes a dedicated evaluation dataset and evaluation pipeline.

Run:

```bash
py evaluation/evaluate.py
```

For detailed per-case output:

```bash
py evaluation/evaluate.py --verbose
```

Save results:

```bash
py evaluation/evaluate.py --output results.json
```

The evaluation dataset contains **60 routing cases** across simple requests, commands, complex requests, ambiguous inputs, and privacy-sensitive requests.

---

# Benchmarking

Run the benchmark:

```bash
py evaluation/benchmark.py
```

Run more iterations:

```bash
py evaluation/benchmark.py --iterations 10
```

Save results:

```bash
py evaluation/benchmark.py --output benchmark_results.json
```

The benchmark measures:

* Signal extraction latency
* Privacy-check latency
* SLM cold-start latency
* SLM warm latency
* End-to-end pipeline latency
* Memory usage

> Benchmark results are hardware-dependent. EdgeRoute does not assume a specific latency or memory figure across machines.

---

# Example Routing Scenarios

## 1. Simple request

```text
Input:
"What is 2 + 2?"

Route:
LOCAL_SIMPLE

Execution:
Local SLM
```

No cloud request is necessary.

---

## 2. Local command

```text
Input:
"Turn on the bedroom light."

Route:
LOCAL_COMMAND

Tool:
turn_on_light

Status:
SUCCESS
```

The tool implementation is simulated for demonstration purposes.

---

## 3. Complex request

```text
Input:
"Write a 1500-word story about a dragon living on Mars."

Route:
CLOUD_COMPLEX
```

The cloud adapter can operate in mock mode or use a configured OpenAI-compatible endpoint.

---

## 4. Privacy-sensitive request

```text
Input:
"My email is user@example.com.
Please summarize my account."
```

```text
Privacy Guard
      │
      ▼
Sensitive information detected
      │
      ▼
Cloud escalation blocked
      │
      ▼
Local handling
```

---

## 5. Ambiguous request

```text
Input:
"Help me with my project."

Route:
AMBIGUOUS
```

The system safely avoids making an unjustified routing decision.

---

# Routing Pipeline

Every request passes through the following stages:

### 1. Signal Extraction

Local deterministic features are extracted from the request:

* Word count
* Command indicators
* Tool indicators
* Complexity indicators
* Mathematical patterns

### 2. Privacy Scan

The request is checked locally for potentially sensitive information.

### 3. Local SLM Classification

Qwen2.5-0.5B produces structured classification information such as:

```json
{
  "intent": "device_control",
  "route": "LOCAL_COMMAND",
  "confidence": 0.92,
  "reason": "The request is a local device control command."
}
```

### 4. Policy Evaluation

The deterministic policy engine validates the SLM output and applies safety rules.

### 5. Execution

The selected route determines where the request is processed:

```text
LOCAL_SIMPLE   → Local SLM
LOCAL_COMMAND  → Local Tool
CLOUD_COMPLEX  → Cloud Adapter
AMBIGUOUS      → Safe fallback
```

---

# Explainability

EdgeRoute exposes the reasoning behind routing decisions.

Example:

```text
Route: LOCAL_COMMAND
Confidence: 92%

Reason chain:

• Extracted signals:
  5 words
  complexity = 0.00
  command = 0.60
  tool = 0.50

• Privacy guard:
  No sensitive data detected.

• SLM classification:
  LOCAL_COMMAND
  confidence = 0.92

• Policy evaluation:
  Command intent confirmed by deterministic signals.

• Execution:
  turn_on_light
```

This makes the router easier to debug and evaluate than a black-box routing system.

---

# Configuration

EdgeRoute is configured through `.env`.

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:0.5b
OLLAMA_TIMEOUT=60

SLM_CONFIDENCE_THRESHOLD=0.70

COMPLEXITY_THRESHOLD=0.70
COMPLEXITY_WORD_THRESHOLD=60

MOCK_CLOUD=true

CLOUD_API_KEY=
CLOUD_MODEL=gpt-4o-mini
CLOUD_API_BASE=https://api.openai.com/v1
```

### Using another local model

Change:

```env
OLLAMA_MODEL=qwen2.5:0.5b
```

to another Ollama-compatible model, for example:

```env
OLLAMA_MODEL=llama3.2:1b
```

---

# Evaluation Dataset

The project includes `evaluation/test_cases.json` containing **60 test cases**.

| Category             |  Cases |
| -------------------- | -----: |
| `LOCAL_SIMPLE`       |     15 |
| `LOCAL_COMMAND`      |     15 |
| `CLOUD_COMPLEX`      |     15 |
| `AMBIGUOUS`          |     10 |
| Privacy / edge cases |      5 |
| **Total**            | **60** |

The dataset includes both straightforward and less obvious examples to evaluate the routing pipeline.

---

# Security Design

EdgeRoute follows several security-oriented principles:

### No hard-coded API keys

Secrets are loaded through environment variables.

### Allowlisted local tools

Local tool execution uses explicit tool mappings rather than arbitrary user-supplied function execution.

### No shell execution from user input

User requests are not directly converted into shell commands.

### Privacy before cloud routing

The privacy guard runs before cloud escalation.

### Local routing

The cloud adapter is not responsible for making the routing decision.

### Safe fallback

Invalid or low-confidence model output can be handled through deterministic routing rules.

---

# Limitations

EdgeRoute is currently a research/prototype system rather than a production-ready inference gateway.

| Limitation                                | Description                                                                                 |
| ----------------------------------------- | ------------------------------------------------------------------------------------------- |
| **Heuristic complexity detection**        | Complexity is estimated using deterministic signals rather than deep semantic understanding |
| **Small SLM**                             | Qwen2.5-0.5B can misclassify difficult edge cases                                           |
| **Regex privacy detection**               | Lightweight detection can miss obfuscated or previously unseen sensitive data               |
| **Simulated tools**                       | Local device operations are simulated                                                       |
| **Cloud dependency for complex requests** | Live cloud inference requires a configured API                                              |
| **Hardware-dependent performance**        | Latency varies significantly across systems                                                 |
| **No GPU requirement**                    | The system is designed around CPU-compatible local inference                                |
| **Edge hardware benchmarking**            | Raspberry Pi deployment has not yet been benchmarked                                        |

---

# Future Work

Potential improvements include:

* **Learned routing models** — replace or complement heuristic routing with a trained lightweight classifier
* **Improved quantization** — optimize local inference for CPU-based edge hardware
* **Raspberry Pi deployment** — benchmark and optimize ARM deployments
* **Adaptive routing** — dynamically tune routing thresholds based on observed outcomes
* **Energy-aware routing** — consider battery and power consumption
* **Cost-aware routing** — estimate cloud token cost before escalation
* **Personalized policies** — support user-specific routing and privacy preferences
* **Production PII detection** — integrate dedicated privacy/NER systems
* **Streaming responses** — improve perceived local inference latency
* **Multi-turn context** — incorporate conversation context into routing decisions

---

# Design Philosophy

EdgeRoute is built around a simple principle:

```text
                 Don't use the cloud
                 unless you need it.
                         │
                         ▼
              ┌─────────────────────┐
              │ Can we handle this   │
              │ locally?             │
              └──────────┬──────────┘
                         │
               ┌─────────┴─────────┐
               │                   │
              YES                  NO
               │                   │
               ▼                   ▼
          Local execution      Cloud escalation
               │                   │
               └─────────┬─────────┘
                         ▼
                    Response
```

This approach aims to reduce unnecessary cloud inference while improving **privacy, resilience, cost efficiency, and suitability for edge environments**.

---

# License

Add the project's chosen license here before publishing the repository publicly.

---

## EdgeRoute

**Local-first AI inference routing for privacy-aware edge applications.**

> **Decide locally. Execute locally. Escalate only when necessary.**
