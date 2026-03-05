"""Static API contract checks for requirements MCP service."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_requirements_mcp_endpoints_declared() -> None:
    src = (ROOT / "requirements-bots/mcp-requirements.js").read_text(encoding="utf-8")
    expected = ["/rvs", "/doors", "/rtm", "/rtm.yaml", "/test-matrix", "SESSION_INIT", "FETCH_RTM"]
    for token in expected:
        assert token in src
