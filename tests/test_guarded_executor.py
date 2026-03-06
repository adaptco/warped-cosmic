from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts" / "moa-cli-coding-fabric" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from guarded_executor import _parse_git_status


def test_parse_git_status_tracks_merge_state() -> None:
    changes = _parse_git_status(
        "\n".join(
            [
                "UU server/agent_protocol.py",
                " M docs/AGENTS.md",
                "?? telemetry/output/rework_summary.json",
            ]
        )
    )

    assert changes[0]["path"] == "server/agent_protocol.py"
    assert changes[0]["unmerged"] is True
    assert changes[1]["unstaged"] is True
    assert changes[2]["untracked"] is True
