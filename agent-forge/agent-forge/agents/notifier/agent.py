"""
agents/notifier/agent.py
Notifier Agent — dispatches implementation plans to Slack and Discord.
Triggered by T-003 (LLM handoff). Notifies agents of tasks via webhooks.
"""
import os, json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
SLACK_WEBHOOK  = os.environ.get("SLACK_WEBHOOK_URL", "")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")


def format_implementation_plan(agent_response: dict) -> dict:
    """Use Claude to format the agent response as a clean implementation plan."""
    resp = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1000,
        system="Format the following agent response as a concise implementation plan with numbered tasks. Use simple markdown. Max 400 chars for Slack/Discord.",
        messages=[{"role": "user", "content": json.dumps(agent_response)}]
    )
    return {"text": resp.content[0].text, "timestamp": datetime.now(timezone.utc).isoformat()}


def send_slack(plan: dict) -> bool:
    if not SLACK_WEBHOOK:
        print("⚠ SLACK_WEBHOOK_URL not set — skipping")
        return False
    payload = {
        "text": "🤖 *Agent Forge: Implementation Plan Ready*",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "⬡ Agent Forge — Implementation Plan"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": plan["text"]}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"_Generated at {plan['timestamp']}_"}]},
        ]
    }
    return _post_webhook(SLACK_WEBHOOK, payload, "Slack")


def send_discord(plan: dict) -> bool:
    if not DISCORD_WEBHOOK:
        print("⚠ DISCORD_WEBHOOK_URL not set — skipping")
        return False
    payload = {
        "content": "**⬡ Agent Forge — Implementation Plan**",
        "embeds": [{
            "title": "New Implementation Plan",
            "description": plan["text"][:2000],
            "color": 0xf59e0b,
            "footer": {"text": f"Agent Forge · {plan['timestamp']}"}
        }]
    }
    return _post_webhook(DISCORD_WEBHOOK, payload, "Discord")


def _post_webhook(url: str, payload: dict, name: str) -> bool:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"✓ {name} webhook: {r.status}")
            return True
    except Exception as e:
        print(f"✗ {name} webhook failed: {e}")
        return False


if __name__ == "__main__":
    agent_response = json.loads(Path("artifacts/agent-response.json").read_text())
    plan = format_implementation_plan(agent_response)
    results = {
        "slack": send_slack(plan),
        "discord": send_discord(plan),
        "plan": plan,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    Path("artifacts/notification-receipt.json").write_text(json.dumps(results, indent=2))
    print(f"✓ Notifications sent — Slack={results['slack']}, Discord={results['discord']}")
