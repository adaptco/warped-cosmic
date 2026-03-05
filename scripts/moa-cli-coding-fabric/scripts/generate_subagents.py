#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "subagents.v1.json"


def payload() -> dict[str, Any]:
    subagents = [
        {
            "id": "Planner",
            "goal": "Convert user request into deterministic execution intent and success criteria.",
            "input_artifact": "task_request",
            "output_artifact": "execution_intent",
            "allowed_tool_classes": ["git", "filesystem", "inventory"],
        },
        {
            "id": "Architect",
            "goal": "Map repo structure, constraints, and implementation approach.",
            "input_artifact": "execution_intent",
            "output_artifact": "architecture_plan",
            "allowed_tool_classes": ["git", "filesystem", "search"],
        },
        {
            "id": "Coder",
            "goal": "Produce candidate code/task actions scoped to the selected repository.",
            "input_artifact": "architecture_plan",
            "output_artifact": "code_actions",
            "allowed_tool_classes": ["git", "python", "node", "build"],
        },
        {
            "id": "Tester",
            "goal": "Validate behavior through deterministic checks and test commands.",
            "input_artifact": "code_actions",
            "output_artifact": "validation_report",
            "allowed_tool_classes": ["pytest", "node", "docker", "terraform", "kubectl", "helm"],
        },
        {
            "id": "Reviewer",
            "goal": "Summarize risk and readiness, then emit final execution envelope.",
            "input_artifact": "validation_report",
            "output_artifact": "final_review",
            "allowed_tool_classes": ["git", "filesystem", "reporting"],
        },
    ]

    handoffs = [
        {"producer": "Planner", "consumer": "Architect", "artifact_type": "execution_intent", "validation_gate": "intent_is_specific"},
        {"producer": "Architect", "consumer": "Coder", "artifact_type": "architecture_plan", "validation_gate": "repo_scope_confirmed"},
        {"producer": "Coder", "consumer": "Tester", "artifact_type": "code_actions", "validation_gate": "commands_policy_checked"},
        {"producer": "Tester", "consumer": "Reviewer", "artifact_type": "validation_report", "validation_gate": "tests_or_checks_completed"},
    ]

    return {
        "schema_version": "1",
        "subagents": subagents,
        "handoffs": handoffs,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic MoA sub-agent contract.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload(), indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
