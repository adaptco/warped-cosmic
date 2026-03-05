# AxQxOS Avatar Engine
### Sovereign Delivery System — v1.0.0

> *Canonical truth, attested and replayable.*

---

## Architecture

```
AxQxOS-Avatar-Engine/
├── .github/workflows/
│   └── avatar-engine.yml       # 8-stage CI/CD pipeline
├── scripts/
│   └── merge-repos.sh          # Sovereign multi-repo merger (single signed commit)
├── mcp-server/
│   ├── index.js                # A2A WebSocket + REST server
│   ├── a2a-arbiter.js          # Codestral-powered task arbitration
│   └── webhook-router.js       # JSON / Markdown / YAML dispatch
├── mlops/
│   └── gemini_lora.py          # Gemini LoRA fine-tuning loop
├── antigravity/
│   └── sandbox.py              # Local weight-tuning sandbox (Gemini rewards)
├── agents/
│   └── avatar_codegen_agent.py # Production AVATAR_CODEGEN agent
├── manifests/
│   ├── firebase-studio.yaml    # Firebase Studio project manifest
│   └── docker-compose.yml      # Local dev stack
└── requirements.txt
```

---

## Pipeline Flow

```
merge-repos.sh
    │  (single signed commit, merge receipt emitted)
    ▼
GitHub Actions: avatar-engine.yml
    │
    ├── [0] Integrity Gate       ← canonical hash, receipt verification
    ├── [1] Lint & Type Check    ← ruff, mypy, eslint
    ├── [2] Unit Tests           ← pytest + coverage
    │
    ├── [3] Antigravity Sandbox  ← Gemini reward scoring (local pre-filter)
    ├── [4] LoRA Fine-Tune       ← Gemini tuning API → tuned model ID
    │
    ├── [5] Docker Build & Push  ← MCP server + Agent images → GHCR
    ├── [6] Firebase Sim         ← Emulator suite validation
    ├── [7] Deploy               ← K8s + deployment receipt
    └── [8] Webhook Notify       ← JSON/MD/YAML payload dispatch
```

---

## Agent Roles

| Role | Description |
|------|-------------|
| `AVATAR_CODEGEN` | Generates embodied Avatar runtime modules (ADK v0) |
| `RAG_RETRIEVER` | Gemini-embedded RAG retrieval pipeline |
| `LORA_TRAINER` | LoRA fine-tune job launcher |
| `WEBHOOK_DISPATCHER` | Multi-format payload dispatcher |

All agents connect to the MCP A2A server via WebSocket. Unrouted tasks are
scaffolded automatically via the Codestral API.

---

## Quick Start

### 1. Merge repos
```bash
chmod +x scripts/merge-repos.sh
./scripts/merge-repos.sh
```

### 2. Run local stack
```bash
cp .env.example .env   # fill GEMINI_API_KEY, CODESTRAL_API_KEY
docker compose -f manifests/docker-compose.yml up
```

### 3. Run Antigravity sandbox (local LoRA pre-scoring)
```bash
docker compose -f manifests/docker-compose.yml --profile tuning up antigravity
```

### 4. Submit a task via webhook
```bash
curl -X POST http://localhost:3001/webhook/task \
  -H "Content-Type: application/json" \
  -d '{
    "targetRole": "AVATAR_CODEGEN",
    "capsule": "Sol.F1",
    "spec": "Generate a runtime locomotion module for Sol.F1 avatar",
    "callbackUrl": "https://your-endpoint.dev/callback"
  }'
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key (MLOps + embeddings) |
| `CODESTRAL_API_KEY` | Codestral API key (A2A scaffolding) |
| `MCP_PORT` | MCP server port (default: 3001) |
| `TUNED_MODEL_ID` | LoRA-tuned model ID (overrides base model) |
| `REWARD_THRESHOLD` | Antigravity reward filter threshold (default: 0.75) |
| `AGENT_CAPSULE` | Avatar capsule binding (default: Sol.F1) |

---

## PRIME_DIRECTIVE

All Avatar render assets are governed by `C5_SYMMETRY`:
- Wheels: **5-spoke Advan GT Beyond** only
- Finish: **Racing Sand Metallic (RSM)**
- Assets: Obsidian/Nocturnal Black (A90 Supra, Aston Martin Vantage VH100)

These physical constants override all AI training defaults.

---

## Canonical Tokens

`AXIS` · `PLUG` · `TRACE` · `BLOOM` · `LUMEN` · `SOULOS`

All simulations use SDE (signal-driven economics) with dynamic trust-weighted TAPD yield.
