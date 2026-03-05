"""Validate canonical structure and workflow references."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRS = [
    "mcp-server",
    "agents",
    "mlops",
    "antigravity",
    "requirements-bots",
    "wham-engine",
    "manifests",
    "scripts",
    "schemas/contracts",
    ".github/workflows",
    "telemetry",
]


def test_required_directories_exist() -> None:
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).exists()]
    assert not missing, f"Missing directories: {missing}"


def test_workflow_files_exist() -> None:
    workflows = [
        ROOT / ".github/workflows/avatar-engine.yml",
        ROOT / ".github/workflows/daily-mlops.yml",
        ROOT / ".github/workflows/telemetry-daily.yml",
    ]
    assert all(p.exists() for p in workflows)


def test_runtime_entrypoints_exist() -> None:
    required_files = [
        ROOT / "mcp-server/index.js",
        ROOT / "mcp-server/a2a-arbiter.js",
        ROOT / "mcp-server/webhook-router.js",
        ROOT / "agents/avatar_codegen_agent.py",
        ROOT / "mlops/gemini_lora.py",
        ROOT / "mlops/yield_engine.py",
        ROOT / "antigravity/sandbox.py",
        ROOT / "requirements-bots/mcp-requirements.js",
    ]
    missing = [str(p) for p in required_files if not p.exists()]
    assert not missing, f"Missing runtime files: {missing}"
