from __future__ import annotations

import json
from collections import Counter

from telemetry.rework_report import (
    build_resolution_candidates,
    extract_file_mentions_from_payload,
    parse_git_status,
)


def test_extract_file_mentions_from_payload() -> None:
    payload = json.dumps(
        {
            "message": {
                "content": "Resolve conflicts in orchestrator/stateflow.py and schemas/database.py.",
            },
            "files_changed": [
                "server/agent_protocol.py",
                "docs/AGENTS.md",
            ],
        }
    )

    mentions = extract_file_mentions_from_payload(payload)

    assert "orchestrator/stateflow.py" in mentions
    assert "schemas/database.py" in mentions
    assert "server/agent_protocol.py" in mentions
    assert "docs/AGENTS.md" in mentions


def test_build_resolution_candidates_prioritizes_conflicts() -> None:
    working_tree = parse_git_status(
        "\n".join(
            [
                "UU server/agent_protocol.py",
                " M docs/AGENTS.md",
                "?? telemetry/output/rework_summary.json",
            ]
        )
    )
    telemetry_mentions = Counter(
        {
            "server/agent_protocol.py": 4,
            "docs/AGENTS.md": 1,
        }
    )

    candidates = build_resolution_candidates(
        working_tree_changes=working_tree,
        branch_changed_files=["server/agent_protocol.py", "api_server.py"],
        telemetry_mentions=telemetry_mentions,
    )

    assert candidates[0]["path"] == "server/agent_protocol.py"
    assert "unmerged" in candidates[0]["reasons"]
    assert any(reason.startswith("telemetry_mentions:") for reason in candidates[0]["reasons"])
