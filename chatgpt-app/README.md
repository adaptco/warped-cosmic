# ChatGPT App: MCP Embedding Studio

Submission-ready ChatGPT App package for A2A_MCP. It exposes hybrid tools:

- `embedding_search` (read)
- `embedding_upsert` (write)
- `embedding_workspace_data` (read)
- `orchestrate_command` (write)
- `render_embedding_workspace` (render helper)

The app uses a vanilla widget (`text/html;profile=mcp-app`) and forwards tool execution to the canonical backend `app.mcp_gateway` `/tools/call`.

## Local Development

1. Copy env template:
   - `cp .env.example .env` (or PowerShell equivalent)
2. Run canonical backend:
   - `uvicorn app.mcp_gateway:app --host 0.0.0.0 --port 8080`
3. Run ChatGPT App server:
   - `npm install`
   - `npm run dev`
4. Expose app through HTTPS tunnel:
   - `ngrok http 8787`
5. In ChatGPT Developer Mode, add app endpoint:
   - `https://<tunnel-domain>/mcp`

## Submission Preflight

- Set `CHATGPT_APP_DOMAIN`, `CHATGPT_APP_PRIVACY_URL`, `CHATGPT_APP_SUPPORT_URL`.
- Configure GitHub OAuth env values (`GITHUB_OAUTH_*`) in deployment secret manager.
- Confirm MCP endpoint is stable public HTTPS (no localhost).
- Validate tool auth:
  - read tools require configured read scope
  - write/orchestration tools require configured write scope
- Confirm widget CSP `connectDomains` and `resourceDomains` match deployed endpoints.
