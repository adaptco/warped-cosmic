# Unified AxQxOS + WHAM Production Pipeline

## Monorepo layout
- `mcp-server/`: A2A routing server
- `agents/`: runtime agents
- `mlops/`: LoRA + yield processing
- `antigravity/`: reward pre-filtering
- `requirements-bots/`: requirements MCP service
- `wham-engine/`: WASM shell and worldline runtime
- `telemetry/`: JSONL ETL and KPI reporting
- `schemas/contracts/`: stable public contracts
- `.github/workflows/`: CI/CD, daily MLOps, telemetry

## Quick start
```bash
cp .env.example .env
pip install -r requirements/base.txt
npm install --prefix mcp-server
npm install --prefix requirements-bots
python telemetry/etl.py --root .
python telemetry/kpi_report.py
```

Runtime model selection is provider-agnostic via:
- `LLM_TARGET=claude|openai|gemini|ollama|any`
- `MODEL_ID=<provider-model-id>`
- Provider secrets (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`) as needed.

## Guardrails
- Required secret checks: `python scripts/check_required_secrets.py`
- Contract validation: `python scripts/validate_schemas.py manifests`
- Receipt signing: `python scripts/sign_receipt.py <receipt.json>`
