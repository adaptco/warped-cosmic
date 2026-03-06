"""Validate that referenced paths in workflows exist in repo."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "mcp-server/index.js",
    "mcp-server/a2a-arbiter.js",
    "mcp-server/webhook-router.js",
    "requirements-bots/mcp-requirements.js",
    "agents/avatar_codegen_agent.py",
    "agents/Dockerfile",
    "antigravity/sandbox.py",
    "mlops/gemini_lora.py",
    "mlops/yield_engine.py",
    "scripts/check_required_secrets.py",
    "scripts/sign_receipt.py",
    "scripts/validate_schemas.py",
    "config/task_library.json",
    "manifests/firebase-studio.yaml",
    "telemetry/rework_report.py",
    ".github/workflows/avatar-engine.yml",
    ".github/workflows/daily-mlops.yml",
    ".github/workflows/telemetry-daily.yml",
]


def main() -> None:
    missing = [p for p in REQUIRED_PATHS if not (ROOT / p).exists()]
    if missing:
        print("Missing workflow-referenced paths:")
        for path in missing:
            print(f"- {path}")
        raise SystemExit(1)

    print(f"Validated {len(REQUIRED_PATHS)} workflow-referenced paths")


if __name__ == "__main__":
    main()
