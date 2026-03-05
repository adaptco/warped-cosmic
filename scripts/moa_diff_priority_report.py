"""Build deterministic multi-repo diff visibility and top-priority recommendations."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_ROOT = Path(r"C:\Users\eqhsp\Documents\GitHub")
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".turbo",
    "backups",
}
RISK_WEIGHTS = {"high": 3.0, "medium": 2.0, "low": 1.0}


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )
    output = (completed.stdout or "").strip() or (completed.stderr or "").strip()
    return completed.returncode, output


def discover_repos(root: Path) -> list[Path]:
    repos: list[Path] = []
    seen: set[str] = set()
    for current, dirs, _ in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        path = Path(current)
        if not (path / ".git").exists():
            continue
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        repos.append(path.resolve())
    return sorted(repos, key=lambda p: str(p).lower())


def parse_status_lines(lines: list[str]) -> tuple[dict[str, int], Counter[str]]:
    status_counts: Counter[str] = Counter()
    path_counts: Counter[str] = Counter()
    for line in lines:
        if len(line) < 4:
            continue
        code = line[:2].strip() or "??"
        status_counts[code] += 1
        path = line[3:]
        if "->" in path:
            path = path.split("->", 1)[1].strip()
        top = re.split(r"[\\/]", path)[0] or "(root)"
        path_counts[top] += 1
    return dict(sorted(status_counts.items())), path_counts


def infer_risk(repo: Path, path_counts: Counter[str]) -> str:
    if (repo / ".github" / "workflows").exists():
        return "high"
    for hot in ("k8s", "helm", "terraform", "infra"):
        if (repo / hot).exists():
            return "high"
    if "Dockerfile" in path_counts or any(k.startswith(".github") for k in path_counts):
        return "high"
    if (repo / "docker-compose.yml").exists() or (repo / "docker-compose.yaml").exists():
        return "medium"
    return "low"


def parse_upstream_counts(value: str) -> tuple[int, int]:
    if not value or "\t" not in value:
        return 0, 0
    left, right = value.split("\t", 1)
    try:
        behind = int(left.strip())
        ahead = int(right.strip())
    except ValueError:
        return 0, 0
    return ahead, behind


def parse_remote_slug(repo: Path) -> str | None:
    code, output = _run(["git", "remote", "get-url", "origin"], cwd=repo)
    if code != 0 or not output:
        return None
    url = output.strip()
    if url.startswith("git@github.com:"):
        path = url.split("git@github.com:", 1)[1]
    else:
        parsed = urlparse(url)
        if parsed.netloc.lower() != "github.com":
            return None
        path = parsed.path.lstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if path.count("/") != 1:
        return None
    return path


def detect_pr_conflict(repo: Path, branch: str) -> dict[str, Any]:
    slug = parse_remote_slug(repo)
    if not slug or not branch:
        return {"pr_conflict": False, "pr_number": None, "mergeable": None, "merge_state_status": None}
    code, output = _run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            slug,
            "--head",
            branch,
            "--state",
            "open",
            "--json",
            "number,mergeable,mergeStateStatus",
            "--limit",
            "1",
        ]
    )
    if code != 0 or not output:
        return {"pr_conflict": False, "pr_number": None, "mergeable": None, "merge_state_status": None}
    try:
        entries = json.loads(output)
    except json.JSONDecodeError:
        entries = []
    if not entries:
        return {"pr_conflict": False, "pr_number": None, "mergeable": None, "merge_state_status": None}
    pr = entries[0]
    mergeable = str(pr.get("mergeable", "")).upper() or None
    merge_state_status = str(pr.get("mergeStateStatus", "")).upper() or None
    pr_conflict = bool(mergeable == "CONFLICTING" or merge_state_status == "DIRTY")
    return {
        "pr_conflict": pr_conflict,
        "pr_number": pr.get("number"),
        "mergeable": mergeable,
        "merge_state_status": merge_state_status,
    }


def priority_score(
    *,
    risk: str,
    changed_files: int,
    ahead: int,
    behind: int,
    pr_conflict: bool,
) -> float:
    risk_weight = RISK_WEIGHTS.get(risk, 1.0)
    pressure = min(changed_files, 300) * 0.20
    divergence = (abs(ahead) + abs(behind)) * 1.5
    conflict_bonus = 15.0 if pr_conflict else 0.0
    return round((risk_weight * 10.0) + pressure + divergence + conflict_bonus, 2)


def recommended_action(*, changed_files: int, ahead: int, behind: int, pr_conflict: bool) -> str:
    if pr_conflict:
        return "Resolve open PR merge conflicts and rerun integration checks."
    if changed_files > 200:
        return "Checkpoint branch and split changes into reviewable batches."
    if behind > 0:
        return "Sync branch with upstream before additional feature work."
    if changed_files > 0:
        return "Run tests and stage a focused commit."
    if ahead > 0:
        return "Prepare push/PR for unmerged local commits."
    return "No immediate action."


def scan_repo(repo: Path) -> dict[str, Any]:
    _, branch = _run(["git", "branch", "--show-current"], cwd=repo)
    branch = branch.strip()

    _, porcelain_raw = _run(["git", "status", "--porcelain"], cwd=repo)
    status_lines = [line for line in porcelain_raw.splitlines() if line.strip()]
    status_counts, path_counts = parse_status_lines(status_lines)
    changed_files = len(status_lines)

    _, ahead_behind_raw = _run(["git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD"], cwd=repo)
    ahead, behind = parse_upstream_counts(ahead_behind_raw)

    risk = infer_risk(repo, path_counts)
    pr_meta = detect_pr_conflict(repo, branch=branch)
    score = priority_score(
        risk=risk,
        changed_files=changed_files,
        ahead=ahead,
        behind=behind,
        pr_conflict=bool(pr_meta["pr_conflict"]),
    )
    action = recommended_action(
        changed_files=changed_files,
        ahead=ahead,
        behind=behind,
        pr_conflict=bool(pr_meta["pr_conflict"]),
    )

    top_paths = [{"path": k, "count": v} for k, v in path_counts.most_common(12)]
    return {
        "repo_path": str(repo),
        "repo_name": repo.name,
        "branch": branch or "HEAD",
        "ahead_behind": {"ahead": ahead, "behind": behind},
        "status_counts": status_counts,
        "changed_files": changed_files,
        "top_paths": top_paths,
        "risk_profile": risk,
        "pr_conflict": bool(pr_meta["pr_conflict"]),
        "pr_number": pr_meta["pr_number"],
        "mergeable": pr_meta["mergeable"],
        "merge_state_status": pr_meta["merge_state_status"],
        "priority_score": score,
        "recommended_action": action,
    }


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Daily Diff Priority Report")
    lines.append("")
    lines.append(f"- Generated at: `{report['generated_at']}`")
    lines.append(f"- Root: `{report['root']}`")
    lines.append(f"- Repositories scanned: `{report['counts']['repos']}`")
    lines.append("")
    lines.append("## Top 3 Priorities")
    lines.append("")
    for idx, item in enumerate(report["top_priorities"], start=1):
        lines.append(
            f"{idx}. `{item['repo_name']}` (`score={item['priority_score']}`) - {item['recommended_action']}"
        )
    lines.append("")
    lines.append("## Repo Summary")
    lines.append("")
    lines.append("| Repo | Branch | Changed | Ahead/Behind | Risk | PR Conflict | Score |")
    lines.append("|---|---|---:|---:|---|---|---:|")
    for item in report["repos"]:
        ab = item["ahead_behind"]
        lines.append(
            f"| `{item['repo_name']}` | `{item['branch']}` | {item['changed_files']} | "
            f"{ab['ahead']}/{ab['behind']} | {item['risk_profile']} | "
            f"{'yes' if item['pr_conflict'] else 'no'} | {item['priority_score']} |"
        )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Root directory to scan.")
    parser.add_argument("--output-json", required=True, help="Output JSON report path.")
    parser.add_argument("--output-md", required=True, help="Output Markdown report path.")
    parser.add_argument("--include-clean", action="store_true", help="Include clean repositories in summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    repos = discover_repos(root)
    results = [scan_repo(repo) for repo in repos]
    if not args.include_clean:
        results = [x for x in results if x["changed_files"] > 0 or x["pr_conflict"]]

    results = sorted(
        results,
        key=lambda x: (
            -float(x["priority_score"]),
            -int(x["changed_files"]),
            x["repo_name"].lower(),
        ),
    )
    top_priorities = results[:3]
    report = {
        "schema_version": "a2a/1.0",
        "goal": "Daily local git diff visibility and top priorities",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "counts": {"repos": len(results)},
        "repos": results,
        "top_priorities": top_priorities,
    }

    out_json = Path(args.output_json).expanduser().resolve()
    out_md = Path(args.output_md).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    out_md.write_text(build_markdown(report), encoding="utf-8")

    print(f"wrote: {out_json}")
    print(f"wrote: {out_md}")
    if report["top_priorities"]:
        print("top3:")
        for idx, item in enumerate(report["top_priorities"], start=1):
            print(f"{idx}. {item['repo_name']} ({item['priority_score']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
