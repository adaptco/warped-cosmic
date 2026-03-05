"""
agents/browser/agent.py
Browser Agent — executes Playwright scripts as WASM-compiled automation routines.
Receives task specs from MCP, executes browser actions, emits results via A2A webhook.
"""
import os, json, asyncio, hashlib
from datetime import datetime, timezone
from pathlib import Path
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

async def execute_browser_task(task_spec: dict) -> dict:
    """
    Uses Claude to generate Playwright script from natural-language task spec,
    then executes it in a headless browser environment.
    """
    # 1. Claude generates the Playwright script
    resp = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1000,
        system="""You are a Playwright browser automation expert.
Given a task specification, generate a complete async Python Playwright script.
Return ONLY the script inside a ```python block. No prose.""",
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
        "output": {}
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
    task_spec = json.loads(spec_path.read_text()) if spec_path.exists() else {
        "id": "demo", "url": "https://example.com", "action": "screenshot"
    }
    result = asyncio.run(execute_browser_task(task_spec))
    Path("artifacts/browser-result.json").write_text(json.dumps(result, indent=2))
    fire_a2a_webhook("T-002", result)
    print(f"✓ Browser task complete: {result['status']}")
