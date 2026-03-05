# MCP Server Integration Patterns

## Universal LLM Adapter Pattern

All LLMs are accessed through a unified adapter so agent code is LLM-agnostic:

```python
# agents/runner.py — LLM router
import os

LLM_TARGET = os.environ["LLM_TARGET"]

def call_llm(system_prompt: str, user_message: str) -> str:
    if LLM_TARGET == "claude":
        return _call_claude(system_prompt, user_message)
    elif LLM_TARGET == "openai":
        return _call_openai(system_prompt, user_message)
    elif LLM_TARGET == "gemini":
        return _call_gemini(system_prompt, user_message)
    elif LLM_TARGET == "ollama":
        return _call_ollama(system_prompt, user_message)
    else:
        raise ValueError(f"Unknown LLM target: {LLM_TARGET}")
```

## MCP Server Registry Pattern

```json
// mcp-registry.json
{
  "schema_version": "1.0",
  "servers": [
    {
      "name": "echo-relay",
      "url": "https://mcp.echo.internal/sse",
      "auth_env": "ECHO_MCP_TOKEN",
      "agents": ["Echo"],
      "purpose": "Cross-LLM webhook relay broker"
    },
    {
      "name": "gloh-rag",
      "url": "https://mcp.gloh.internal/sse",
      "auth_env": "GLOH_MCP_TOKEN",
      "agents": ["Gloh"],
      "purpose": "Vector store retrieval"
    }
  ]
}
```

## Echo Relay Pattern

Echo is the single broker for all cross-LLM messages:

```
Agent A (Claude) → POST webhook_out → Echo MCP endpoint
Echo MCP → route by to_agent.llm_target → Agent B (OpenAI)
Agent B → POST webhook_out → Echo MCP endpoint
Echo MCP → route → Agent C (Gemini)
```

Echo's MCP server validates envelope schema, logs to receipts/, then forwards.

## GitHub Actions Secrets Required

| Secret Name | Used By |
|-------------|---------|
| ANTHROPIC_API_KEY | Claude agents |
| OPENAI_API_KEY | GPT agents |
| GEMINI_API_KEY | Gemini agents |
| OLLAMA_HOST | Local OSS agents |
| ECHO_MCP_TOKEN | Echo relay |
| GLOH_MCP_TOKEN | Gloh RAG |
| GITHUB_TOKEN | Auto-provided by Actions |

## Ollama Local Pattern

For local/OSS models via Ollama, the runner uses a self-hosted runner or Codespaces:
- Install Ollama on the runner: `curl -fsSL https://ollama.com/install.sh | sh`
- Pull model: `ollama pull mistral`
- Point `OLLAMA_HOST` to `http://localhost:11434`
