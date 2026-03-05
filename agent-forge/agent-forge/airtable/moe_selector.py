"""
airtable/moe_selector.py
Airtable Mixture-of-Experts Selector
Reads the agent_mixture table to select the optimal LLM composition for the current task.
Writes selected mixture back to artifacts for downstream orchestration.
"""
import os, json
from pathlib import Path
from datetime import datetime, timezone

# Airtable base config — set in env or .env file
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY", "")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "")
AIRTABLE_TABLE   = "agent_mixture"

# ─── Airtable Schema (create this table in your Airtable base) ────────────────
AIRTABLE_SCHEMA = {
  "table_name": "agent_mixture",
  "fields": [
    {"name": "agent_id",      "type": "singleLineText",  "description": "Unique agent ID (claude, gpt4, gemini, vertex)"},
    {"name": "agent_name",    "type": "singleLineText",  "description": "Display name"},
    {"name": "vendor",        "type": "singleLineText",  "description": "Anthropic | OpenAI | Google"},
    {"name": "model_string",  "type": "singleLineText",  "description": "API model ID"},
    {"name": "weight_pct",    "type": "number",          "description": "Mixture weight 0-100"},
    {"name": "task_scope",    "type": "multipleSelects", "description": "scaffold | chat | ui-gen | ux | wasm | mobile"},
    {"name": "mcp_binding",   "type": "url",             "description": "MCP server URL or empty"},
    {"name": "active_flag",   "type": "checkbox",        "description": "Include in current mixture"},
    {"name": "api_key_env",   "type": "singleLineText",  "description": "Name of env var holding API key"},
    {"name": "cost_per_1k",   "type": "currency",        "description": "Cost per 1k tokens USD"},
    {"name": "notes",         "type": "longText",        "description": "Agent-specific notes"},
  ]
}

# ─── Default mixture (used when Airtable is unavailable) ─────────────────────
DEFAULT_MIXTURE = [
  {"agent_id": "claude",  "agent_name": "Claude",     "vendor": "Anthropic", "model_string": "claude-sonnet-4-20250514", "weight_pct": 35, "task_scope": ["scaffold","enforce","compile"], "active_flag": True, "api_key_env": "ANTHROPIC_API_KEY"},
  {"agent_id": "gpt4",    "agent_name": "GPT-4o",     "vendor": "OpenAI",    "model_string": "gpt-4o",                   "weight_pct": 25, "task_scope": ["chat","mobile","ux-copy"],       "active_flag": True, "api_key_env": "OPENAI_API_KEY"},
  {"agent_id": "gemini",  "agent_name": "Gemini Pro",  "vendor": "Google",   "model_string": "gemini-2.0-flash",        "weight_pct": 25, "task_scope": ["ui-gen","firebase-studio"],      "active_flag": True, "api_key_env": "GEMINI_API_KEY"},
  {"agent_id": "vertex",  "agent_name": "Vertex AI",   "vendor": "Google",   "model_string": "text-bison@002",          "weight_pct": 15, "task_scope": ["ux","wasm"],                     "active_flag": True, "api_key_env": "GOOGLE_APPLICATION_CREDENTIALS"},
]


def fetch_mixture_from_airtable() -> list[dict]:
    """Fetch active agent mixture rows from Airtable."""
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("⚠ Airtable credentials not set — using default mixture")
        return DEFAULT_MIXTURE
    try:
        import urllib.request
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}?filterByFormula={{active_flag}}=1"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {AIRTABLE_API_KEY}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        records = [rec["fields"] for rec in data.get("records", [])]
        return records if records else DEFAULT_MIXTURE
    except Exception as e:
        print(f"⚠ Airtable fetch failed: {e} — using default mixture")
        return DEFAULT_MIXTURE


def select_agent_for_task(task_scope: str, mixture: list[dict]) -> dict:
    """Select the best agent for a given task scope based on mixture weights."""
    candidates = [a for a in mixture if task_scope in a.get("task_scope", []) and a.get("active_flag")]
    if not candidates:
        candidates = mixture  # fallback: any active agent
    # Weighted random selection
    import random
    total = sum(a["weight_pct"] for a in candidates)
    r = random.uniform(0, total)
    cumulative = 0
    for agent in candidates:
        cumulative += agent["weight_pct"]
        if r <= cumulative:
            return agent
    return candidates[0]


if __name__ == "__main__":
    mixture = fetch_mixture_from_airtable()
    output = {
        "mixture": mixture,
        "total_weight": sum(a["weight_pct"] for a in mixture),
        "active_agents": len([a for a in mixture if a.get("active_flag")]),
        "selection_example": {
            "scaffold": select_agent_for_task("scaffold", mixture)["agent_id"],
            "ui-gen":   select_agent_for_task("ui-gen", mixture)["agent_id"],
            "wasm":     select_agent_for_task("wasm", mixture)["agent_id"],
        },
        "airtable_schema": AIRTABLE_SCHEMA,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    Path("artifacts/airtable-mixture.json").write_text(json.dumps(output, indent=2))
    print(f"✓ MoE mixture: {output['active_agents']} active agents")
    print(f"  Example selections: {output['selection_example']}")
