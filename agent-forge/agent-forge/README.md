# ⬡ Agent Forge — Multi-LLM Browser Orchestration

> Claude scaffolds the project. ChatGPT handles mobile. Gemini builds the UI. Vertex generates the UX. WASM runs it all.

---

## Architecture

```
[ChatGPT Mobile]
       │  (message)
       ▼
[Claude Artifact] ─── scaffold generation
       │
       ▼
[Browser Agent (Playwright WASM)] ─→ [MCP Tool Router]
       │                                     │
       ▼                                     ▼
[LLM MoE Handoff] ←──── [Airtable MoE Selector]
Claude 35% / GPT-4o 25% / Gemini 25% / Vertex 15%
       │
       ├──→ [Slack Webhook] ──→ notify agents
       ├──→ [Discord Webhook] ──→ notify agents
       │
       ▼
[Notion / ClickUp] ─── implementation plan as tasks
       │
       ▼
[Zapier Orchestration] ─── cloud job routing
       │
       ├──→ [Gemini + Firebase Studio] ─── UI generation
       └──→ [Vertex AI + WASM Compile] ─── UX + runtime
                    │
                    ▼
            [GitHub Actions] ─→ [Firebase Hosting] ─→ LIVE
```

---

## Quickstart

### 1. Clone + configure
```bash
git clone https://github.com/your-org/agent-forge
cd agent-forge
cp .env.example .env
# Fill in all API keys in .env
```

### 2. Install dependencies
```bash
pip install anthropic playwright pyyaml google-generativeai firebase-admin
playwright install chromium
npm install -g firebase-tools
```

### 3. Set up Airtable
Create a base with table `agent_mixture` using the schema in `airtable/moe_selector.py`.
Add your four agent rows with weights 35/25/25/15.

### 4. Configure webhooks
- **Slack**: Create incoming webhook in Slack App settings → copy to `SLACK_WEBHOOK_URL`
- **Discord**: Server Settings → Integrations → Webhooks → copy to `DISCORD_WEBHOOK_URL`

### 5. Set up Notion/ClickUp
- Notion: Create integration + share database → copy key + DB ID
- ClickUp: Get API key + list ID from workspace settings

### 6. Run locally
```bash
# Run full pipeline
python agents/browser/agent.py

# Or trigger via GitHub Actions
git push origin main
```

### 7. Firebase deploy
```bash
firebase login
firebase use agent-forge-prod
firebase deploy
```

---

## GitHub Actions Secrets

Set all values from `.env.example` as GitHub repository secrets:

```
Settings → Secrets and variables → Actions → New repository secret
```

---

## MCP Server Configuration

The `mcp/config.json` registers all tool endpoints. For Claude Desktop / Claude Code:

```json
// Add to claude_desktop_config.json
{
  "mcpServers": {
    "agent-forge": {
      "command": "python",
      "args": ["mcp/server.py"],
      "env": { "AGENT_FORGE_ENV": "local" }
    }
  }
}
```

---

## Airtable MoE Schema

| Field          | Type            | Description                              |
|----------------|-----------------|------------------------------------------|
| agent_id       | Single line     | claude / gpt4 / gemini / vertex          |
| model_string   | Single line     | Full model API string                    |
| weight_pct     | Number          | Mixture weight 0–100                     |
| task_scope     | Multi-select    | scaffold / chat / ui-gen / ux / wasm     |
| mcp_binding    | URL             | MCP server URL or empty                  |
| active_flag    | Checkbox        | Include in current run                   |
| api_key_env    | Single line     | Env var name containing the API key      |

---

## WASM Module

The browser agent compiles to `wasm32-unknown-unknown` via Rust + `wasm-bindgen`.

```bash
cargo build --target wasm32-unknown-unknown --release
wasm-bindgen target/.../agent_forge.wasm --out-dir wasm/
```

Vertex AI generates the UX wrapper that embeds the WASM module in Firebase Hosting.

---

## License
MIT — Agent Forge
