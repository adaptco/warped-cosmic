"""
agents/browser/agent.py
Browser Agent — executes Playwright scripts as WASM-compiled automation routines.
Receives task specs from MCP, executes browser actions, emits results via A2A webhook.
"""
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.agent_protocol import default_agent_document_paths, get_agent_document_spec

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
BROWSER_AGENT_PROFILE = os.getenv("BROWSER_AGENT_PROFILE", "CLAUDE_BROWSER")


def load_browser_agent_profile() -> dict:
    spec = get_agent_document_spec(
        BROWSER_AGENT_PROFILE,
        default_agent_document_paths(PROJECT_ROOT),
    ) or get_agent_document_spec(
        "SPRYTE",
        default_agent_document_paths(PROJECT_ROOT),
    )
    if spec is None:
        return {
            "agent_name": BROWSER_AGENT_PROFILE,
            "role": "Browser Automation Agent",
            "capsule": "",
            "version": "1.0.0",
            "capabilities": [],
            "tools": [],
            "sources": [],
        }
    return spec.to_dict()


def build_system_prompt(profile: dict) -> str:
    capabilities = profile.get("capabilities", [])
    capability_lines = [
        f"- {cap.get('description') or cap.get('name')}"
        for cap in capabilities
    ] or ["- Playwright browser task execution"]
    tool_lines = [f"- {tool}" for tool in profile.get("tools", [])] or [
        "- Local Playwright runtime"
    ]
    source_lines = [f"- {source}" for source in profile.get("sources", [])] or [
        "- docs/AGENTS.md"
    ]
    role = profile.get("role") or "Browser automation and coding-artifact coordination"
    return "\n".join(
        [
            f"You are {profile.get('agent_name', BROWSER_AGENT_PROFILE)}.",
            f"Role: {role}",
            "Use the agent registry as hard constraints when generating browser automation.",
            "Registry sources:",
            *source_lines,
            "Registered capabilities:",
            *capability_lines,
            "Registered tools:",
            *tool_lines,
            "Given a task specification, generate a complete async Python Playwright script.",
            "When repository work is involved, include outputs that name changed files and artifact paths so CI/CD and guarded executors can reason about merge-back-to-main rework.",
            "Return ONLY the script inside a ```python block. No prose.",
        ]
    )


def emit_agent_profile_artifact(profile: dict, artifacts_dir: Path) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    destination = artifacts_dir / "browser-agent-capabilities.json"
    destination.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return destination

async def execute_browser_task(task_spec: dict) -> dict:
    """
    Uses Claude to generate Playwright script from natural-language task spec,
    then executes it in a headless browser environment.
    """
    profile = load_browser_agent_profile()
    # 1. Claude generates the Playwright script
    resp = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1000,
        system=build_system_prompt(profile),
        messages=[{"role": "user", "content": f"Task: {json.dumps(task_spec)}"}]
    )
    script_block = resp.content[0].text
    # Extract script from code block
    lines = script_block.split("\n")
    script_lines = [l for l in lines if not l.startswith("```")]
    script = "\n".join(script_lines)

    # 2. Execute script (requires playwright installed + DISPLAY or xvfb)
    result = {
        "task_id": task_spec.get("id"),
        "script_hash": hashlib.sha256(script.encode()).hexdigest()[:16],
        "status": "executed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output": {},
        "agent_profile": {
            "agent_name": profile.get("agent_name"),
            "role": profile.get("role"),
            "capsule": profile.get("capsule"),
            "sources": profile.get("sources", []),
            "capabilities": [
                cap.get("name") for cap in profile.get("capabilities", [])
            ],
        },
    }

    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            # Execute generated script in page context
            local_ns = {"page": page, "result": result}
            exec(compile(script, "<browser-agent>", "exec"), local_ns)
            result["output"] = local_ns.get("output", {})
            await browser.close()
    except ImportError:
        result["status"] = "playwright_not_available"
        result["output"] = {"note": "Install: pip install playwright && playwright install chromium"}
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def fire_a2a_webhook(next_task: str, payload: dict):
    import urllib.request
    envelope = {
        "envelope_version": "1.0", "task_id": "T-001",
        "from_agent": "BrowserAgent", "to_agent": "MCPRouter",
        "payload": payload, "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    data = json.dumps(envelope).encode()
    req = urllib.request.Request(
        f"http://echo-relay/webhook/{next_task}", data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Webhook error: {e}")


if __name__ == "__main__":
    spec_path = Path("task_spec.json")
    artifacts_dir = Path("artifacts")
    task_spec = json.loads(spec_path.read_text()) if spec_path.exists() else {
        "id": "demo", "url": "https://example.com", "action": "screenshot"
    }
    profile_artifact = emit_agent_profile_artifact(
        load_browser_agent_profile(),
        artifacts_dir,
    )
    result = asyncio.run(execute_browser_task(task_spec))
    result["agent_profile_artifact"] = str(profile_artifact)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "browser-result.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    fire_a2a_webhook("T-002", result)
    print(f"✓ Browser task complete: {result['status']}")
