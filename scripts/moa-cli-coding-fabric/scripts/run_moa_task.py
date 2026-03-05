#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from guarded_executor import run_guarded_commands  # noqa: E402

DEFAULT_GITHUB_ROOT = Path(r"C:\Users\eqhsp\Documents\GitHub")
DEFAULT_A2A_ROOT = DEFAULT_GITHUB_ROOT / "A2A_MCP"
DEFAULT_MANIFEST = DEFAULT_A2A_ROOT / "ssot" / "manifests" / "rag" / "qube_core" / "simulation" / "CURRENT.json"
DEFAULT_POLICY = SKILL_DIR / "assets" / "cli_policy.v1.yaml"
DEFAULT_ROUTER = SKILL_DIR / "assets" / "router_policy.v1.json"
DEFAULT_SUBAGENTS = SKILL_DIR / "assets" / "subagents.v1.json"
DEFAULT_INVENTORY = SKILL_DIR / "assets" / "repo_inventory.json"


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except Exception:
        return 1, ""
    output = (completed.stdout or "").strip() or (completed.stderr or "").strip()
    return completed.returncode, output


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _resolve_codex_home() -> Path:
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return SKILL_DIR.parent.parent.resolve()


def _ensure_inventory(inventory_path: Path, root: Path) -> dict[str, Any]:
    if not inventory_path.exists():
        bootstrap = SCRIPT_DIR / "bootstrap_repo_inventory.py"
        cmd = [sys.executable, str(bootstrap), "--root", str(root), "--output", str(inventory_path)]
        code, out = _run(cmd)
        if code != 0:
            raise RuntimeError(f"Failed to build inventory: {out}")
    return _load_json(inventory_path)


def _select_repo_entry(inventory: dict[str, Any], repo_path: Path) -> dict[str, Any]:
    repos = inventory.get("repos", [])
    target = str(repo_path.resolve()).lower()
    for item in repos:
        if str(item.get("path", "")).lower() == target:
            return item
    return {
        "name": repo_path.name,
        "path": str(repo_path.resolve()),
        "languages": [],
        "recommended_test_commands": [],
        "recommended_build_commands": [],
        "risk_profile": "unknown",
    }


def _infer_intent(task: str, router_policy: dict[str, Any]) -> str:
    text = task.lower()
    keywords: dict[str, list[str]] = router_policy.get("intent_keywords", {})
    for intent, words in sorted(keywords.items(), key=lambda kv: kv[0]):
        for token in words:
            if token.lower() in text:
                return intent
    return router_policy.get("default_intent", "general_coding")


def _route(intent: str, router_policy: dict[str, Any], subagents: dict[str, Any]) -> dict[str, Any]:
    routes = router_policy.get("intent_routes", {})
    route = routes.get(intent, routes.get(router_policy.get("default_intent", "general_coding"), {}))
    all_ids = [str(x.get("id")) for x in subagents.get("subagents", [])]
    order = route.get("agent_order", all_ids)
    focus = route.get("focus", {})
    return {"intent": intent, "agent_order": order, "focus": focus}


def _docker_healthy() -> bool:
    code, _ = _run(["docker", "ps"])
    return code == 0


def _pgvector_readiness(manifest_path: Path, force_ready: bool) -> dict[str, Any]:
    manifest_exists = manifest_path.exists()
    docker_ok = _docker_healthy()
    ready = bool(force_ready or (manifest_exists and docker_ok))
    return {
        "force_ready": force_ready,
        "manifest_path": str(manifest_path),
        "manifest_exists": manifest_exists,
        "docker_healthy": docker_ok,
        "ready": ready,
    }


def _deterministic_context(repo: Path) -> list[dict[str, Any]]:
    candidates = [
        repo / "README.md",
        repo / "pyproject.toml",
        repo / "requirements.txt",
        repo / "package.json",
        repo / "pnpm-lock.yaml",
        repo / "Dockerfile",
    ]
    out: list[dict[str, Any]] = []
    for path in candidates:
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        preview = (raw.splitlines()[0] if raw.splitlines() else "")[:140]
        out.append({"file": str(path), "sha256_16": digest, "preview": preview})
    return out


def _choose_test_command(repo: Path, repo_entry: dict[str, Any]) -> str:
    tests = repo_entry.get("recommended_test_commands") or []
    if tests:
        return str(tests[0])
    if (repo / "package.json").exists():
        if (repo / "pnpm-lock.yaml").exists():
            return "pnpm test"
        return "npm test"
    return "python -m pytest -q"


def _build_commands(repo: Path, task: str, route: dict[str, Any], repo_entry: dict[str, Any]) -> list[dict[str, Any]]:
    test_cmd = _choose_test_command(repo, repo_entry)
    commands: list[dict[str, Any]] = []
    for idx, agent in enumerate(route["agent_order"], start=1):
        if agent == "Planner":
            cmd = "git status --short"
            reason = "Snapshot working tree state before changes."
        elif agent == "Architect":
            cmd = "git ls-files"
            reason = "List tracked files to scope architecture edits."
        elif agent == "Coder":
            cmd = f'python -c "print(\'Coder stage prepared for task: {task[:80]}\')"'
            reason = "Create deterministic coding stage marker."
        elif agent == "Tester":
            cmd = test_cmd
            reason = "Run primary test command for repository."
        elif agent == "Reviewer":
            cmd = "git diff --stat"
            reason = "Summarize candidate change footprint."
        else:
            cmd = "git status --short"
            reason = "Fallback inspection command."

        commands.append(
            {
                "id": idx,
                "agent": agent,
                "command": cmd,
                "tool_class": "core",
                "reason": reason,
            }
        )

    lower_task = task.lower()
    if any(token in lower_task for token in ["deploy", "release", "k8s", "helm", "terraform", "cluster"]):
        extra = [
            ("docker --version", "Check Docker CLI availability."),
            ("kubectl version --client", "Check kubectl client."),
            ("helm version", "Check Helm availability."),
            ("terraform version", "Check Terraform availability."),
        ]
        base = len(commands)
        for offset, (cmd, reason) in enumerate(extra, start=1):
            commands.append(
                {
                    "id": base + offset,
                    "agent": "Tester",
                    "command": cmd,
                    "tool_class": "devops",
                    "reason": reason,
                }
            )

    return commands


def _slug(text: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return clean[:24] or "task"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a MoE-routed MoA coding task with guarded CLI.")
    parser.add_argument("--repo", required=True, help="Target repository path.")
    parser.add_argument("--task", required=True, help="Task description.")
    parser.add_argument("--intent", default="auto", help="Intent override or 'auto'.")
    parser.add_argument("--mode", choices=["auto", "pgvector", "deterministic"], default="auto")
    parser.add_argument("--execute", action="store_true", help="Execute routed commands.")
    parser.add_argument("--confirm-risk", action="store_true", help="Allow high-risk command execution.")
    parser.add_argument("--manifest-path", default=str(DEFAULT_MANIFEST), help="Path to pgvector manifest.")
    parser.add_argument(
        "--github-root",
        default=str(DEFAULT_GITHUB_ROOT),
        help="Root folder containing repositories for inventory discovery.",
    )
    parser.add_argument("--inventory-path", default=str(DEFAULT_INVENTORY), help="Inventory JSON path.")
    parser.add_argument("--policy-path", default=str(DEFAULT_POLICY), help="CLI policy path.")
    parser.add_argument("--router-policy-path", default=str(DEFAULT_ROUTER), help="Router policy path.")
    parser.add_argument("--subagents-path", default=str(DEFAULT_SUBAGENTS), help="Sub-agent schema path.")
    parser.add_argument("--force-pgvector-ready", action="store_true", help="Force pgvector ready in auto mode.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    codex_home = _resolve_codex_home()
    repo = Path(args.repo).expanduser().resolve()
    inventory_path = Path(args.inventory_path).expanduser().resolve()
    github_root = Path(args.github_root).expanduser().resolve()
    policy_path = Path(args.policy_path).expanduser().resolve()
    router_policy_path = Path(args.router_policy_path).expanduser().resolve()
    subagents_path = Path(args.subagents_path).expanduser().resolve()
    manifest_path = Path(args.manifest_path).expanduser().resolve()

    if not repo.exists():
        raise FileNotFoundError(f"Repo does not exist: {repo}")

    inventory = _ensure_inventory(inventory_path=inventory_path, root=github_root)
    repo_entry = _select_repo_entry(inventory, repo)
    router_policy = _load_json(router_policy_path)
    subagents = _load_json(subagents_path)

    effective_intent = args.intent if args.intent != "auto" else _infer_intent(args.task, router_policy)
    route = _route(effective_intent, router_policy, subagents)

    force_ready = bool(args.force_pgvector_ready or os.getenv("MOA_FORCE_PGVECTOR_READY") == "1")
    readiness = _pgvector_readiness(manifest_path, force_ready=force_ready)
    if args.mode == "auto":
        effective_mode = "pgvector" if readiness["ready"] else "deterministic"
    else:
        effective_mode = args.mode

    commands = _build_commands(repo=repo, task=args.task, route=route, repo_entry=repo_entry)
    deterministic_context = _deterministic_context(repo)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = codex_home / "tmp" / "moa" / "runs" / f"{timestamp}-{_slug(args.task)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    plan: dict[str, Any] = {
        "schema_version": "1",
        "run_id": run_dir.name,
        "repo": {
            "name": repo_entry.get("name"),
            "path": str(repo),
            "risk_profile": repo_entry.get("risk_profile"),
        },
        "task": args.task,
        "intent": {"requested": args.intent, "effective": effective_intent},
        "mode": {"requested": args.mode, "effective": effective_mode, "pgvector_readiness": readiness},
        "routing": route,
        "retrieval": {
            "source": effective_mode,
            "deterministic_context": deterministic_context,
            "manifest_path": str(manifest_path),
        },
        "commands": commands,
    }
    hash_source = {
        "repo": plan["repo"],
        "task": plan["task"],
        "intent": plan["intent"],
        "mode": plan["mode"],
        "routing": plan["routing"],
        "retrieval": plan["retrieval"],
        "commands": plan["commands"],
    }
    plan_hash = hashlib.sha256(json.dumps(hash_source, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    plan["plan_hash"] = plan_hash

    execution = run_guarded_commands(
        commands=commands,
        cwd=repo,
        policy_path=policy_path,
        execute=bool(args.execute),
        confirm_risk=bool(args.confirm_risk),
        timeout_sec=300,
    )
    execution["run_id"] = run_dir.name
    execution["plan_hash"] = plan_hash
    execution["mode_effective"] = effective_mode

    plan_path = run_dir / "plan.json"
    execution_path = run_dir / "execution.json"
    _write_json(plan_path, plan)
    _write_json(execution_path, execution)

    print(f"run_dir: {run_dir}")
    print(f"plan: {plan_path}")
    print(f"execution: {execution_path}")
    print(f"mode: {effective_mode}")
    print(f"plan_hash: {plan_hash}")
    print(f"summary: {json.dumps(execution['summary'], ensure_ascii=True)}")

    if args.execute and execution["summary"]["failed"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
