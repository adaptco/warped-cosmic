#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "assets" / "cli_policy.v1.yaml"


def load_policy(policy_path: Path) -> dict[str, Any]:
    text = policy_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Policy file is empty: {policy_path}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Policy is not valid JSON-compatible YAML: {policy_path}") from exc


def _extract_tool(command: str) -> str:
    try:
        parts = shlex.split(command, posix=False)
    except ValueError:
        parts = command.split()
    if not parts:
        return ""
    name = Path(parts[0]).name.lower()
    if name.endswith(".exe"):
        name = name[:-4]
    return name


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...<truncated>"


def evaluate_command(command: str, policy: dict[str, Any]) -> dict[str, Any]:
    normalized = command.strip().lower()
    tool = _extract_tool(command)
    deny_patterns = [str(x).lower() for x in policy.get("deny_patterns", [])]
    high_risk_patterns = [str(x).lower() for x in policy.get("high_risk_patterns", [])]
    medium_risk_patterns = [str(x).lower() for x in policy.get("medium_risk_patterns", [])]
    allowed_tools = {str(x).lower() for x in policy.get("allowed_tool_prefixes", [])}
    command_prefix_allowlist = [str(x).lower() for x in policy.get("command_prefix_allowlist", [])]

    for pattern in deny_patterns:
        if pattern and pattern in normalized:
            return {
                "allowed": False,
                "risk": "high",
                "tool": tool,
                "reason": f"deny_pattern:{pattern}",
            }

    is_tool_allowed = tool in allowed_tools
    is_prefix_allowed = any(normalized.startswith(p) for p in command_prefix_allowlist if p)
    if not (is_tool_allowed or is_prefix_allowed):
        return {
            "allowed": False,
            "risk": "medium",
            "tool": tool,
            "reason": "tool_not_allowlisted",
        }

    risk = "low"
    for pattern in high_risk_patterns:
        if pattern and pattern in normalized:
            risk = "high"
            break
    if risk != "high":
        for pattern in medium_risk_patterns:
            if pattern and pattern in normalized:
                risk = "medium"
                break

    return {
        "allowed": True,
        "risk": risk,
        "tool": tool,
        "reason": "ok",
    }


def run_guarded_commands(
    commands: list[dict[str, Any]],
    cwd: Path,
    policy_path: Path,
    execute: bool,
    confirm_risk: bool,
    timeout_sec: int = 300,
) -> dict[str, Any]:
    policy = load_policy(policy_path)
    require_confirm_for = set(str(x).lower() for x in policy.get("require_confirm_for_risk", ["high"]))
    max_out = int(policy.get("max_output_chars", 6000))

    results: list[dict[str, Any]] = []
    for idx, item in enumerate(commands, start=1):
        command = str(item.get("command", "")).strip()
        evaluation = evaluate_command(command, policy)
        record: dict[str, Any] = {
            "id": item.get("id", idx),
            "agent": item.get("agent"),
            "command": command,
            "policy": evaluation,
            "status": "dry_run",
            "exit_code": None,
            "stdout": "",
            "stderr": "",
        }

        if not evaluation["allowed"]:
            record["status"] = "blocked"
            results.append(record)
            continue

        risk = str(evaluation["risk"]).lower()
        if execute and risk in require_confirm_for and not confirm_risk:
            record["status"] = "blocked_confirmation_required"
            results.append(record)
            continue

        if not execute:
            results.append(record)
            continue

        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd),
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            record["exit_code"] = completed.returncode
            record["stdout"] = _truncate(completed.stdout or "", max_out)
            record["stderr"] = _truncate(completed.stderr or "", max_out)
            record["status"] = "success" if completed.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            record["status"] = "timeout"
            record["stderr"] = f"Command timed out after {timeout_sec}s"
        results.append(record)

    summary = {
        "total": len(results),
        "dry_run": sum(1 for x in results if x["status"] == "dry_run"),
        "success": sum(1 for x in results if x["status"] == "success"),
        "failed": sum(1 for x in results if x["status"] == "failed"),
        "blocked": sum(1 for x in results if x["status"] == "blocked"),
        "blocked_confirmation_required": sum(1 for x in results if x["status"] == "blocked_confirmation_required"),
        "timeout": sum(1 for x in results if x["status"] == "timeout"),
    }

    return {
        "policy_path": str(policy_path.resolve()),
        "cwd": str(cwd.resolve()),
        "execute": execute,
        "confirm_risk": confirm_risk,
        "results": results,
        "summary": summary,
    }


def _load_commands(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("commands", [])
    if not isinstance(raw, list):
        raise ValueError("commands-json must be a list or {commands:[...]}")
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(raw, start=1):
        if isinstance(item, str):
            out.append({"id": idx, "agent": None, "command": item})
        elif isinstance(item, dict):
            out.append(item)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guarded CLI command executor for MoA coding fabric.")
    parser.add_argument("--repo", required=True, help="Repository working directory.")
    parser.add_argument("--commands-json", required=True, help="JSON file containing command list.")
    parser.add_argument("--policy-path", default=str(DEFAULT_POLICY_PATH), help="Policy path.")
    parser.add_argument("--execute", action="store_true", help="Execute allowed commands. Default is dry run.")
    parser.add_argument("--confirm-risk", action="store_true", help="Allow high-risk command execution.")
    parser.add_argument("--timeout-sec", type=int, default=300, help="Per-command timeout.")
    parser.add_argument("--output-json", help="Optional output result path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    commands_json = Path(args.commands_json).expanduser().resolve()
    policy_path = Path(args.policy_path).expanduser().resolve()

    commands = _load_commands(commands_json)
    report = run_guarded_commands(
        commands=commands,
        cwd=repo,
        policy_path=policy_path,
        execute=bool(args.execute),
        confirm_risk=bool(args.confirm_risk),
        timeout_sec=int(args.timeout_sec),
    )

    if args.output_json:
        out = Path(args.output_json).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        print(f"wrote: {out}")
    else:
        print(json.dumps(report, indent=2, ensure_ascii=True))

    summary = report["summary"]
    if args.execute and (summary["failed"] > 0 or summary["blocked"] > 0 or summary["timeout"] > 0):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
