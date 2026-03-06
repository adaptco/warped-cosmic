"""Build a telemetry-backed rework summary for merge-back-to-main coordination."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

FILE_PATH_RE = re.compile(
    r"(?:[A-Za-z0-9_.-]+[\\/])+[A-Za-z0-9_.-]+\.(?:py|js|ts|tsx|jsx|json|ya?ml|md|txt|toml|ini|sql)"
)
UNMERGED_STATUSES = {"AA", "AU", "DD", "DU", "UA", "UD", "UU"}


def normalize_path(value: str) -> str:
    return value.replace("\\", "/").strip().lstrip("./")


def iter_payload_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for child in value.values():
            yield from iter_payload_strings(child)
        return
    if isinstance(value, list):
        for child in value:
            yield from iter_payload_strings(child)


def extract_file_mentions_from_payload(payload_json: str) -> list[str]:
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        payload = payload_json

    matches: list[str] = []
    for text in iter_payload_strings(payload):
        for raw_path in FILE_PATH_RE.findall(text):
            matches.append(normalize_path(raw_path))
    return matches


def collect_telemetry_file_mentions(db_path: Path) -> Counter[str]:
    mentions: Counter[str] = Counter()
    if not db_path.exists():
        return mentions

    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute("SELECT payload_json FROM session_events").fetchall()
    finally:
        conn.close()

    for (payload_json,) in rows:
        mentions.update(extract_file_mentions_from_payload(payload_json))
    return mentions


def _run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        return None
    return completed


def parse_git_status(output: str) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        status = line[:2]
        raw_path = line[3:]
        path = raw_path.split(" -> ")[-1]
        changes.append(
            {
                "path": normalize_path(path),
                "status": status,
                "staged": status[0] not in {" ", "?", "!"} if len(status) > 0 else False,
                "unstaged": status[1] not in {" ", "?"} if len(status) > 1 else False,
                "untracked": status == "??",
                "unmerged": status in UNMERGED_STATUSES,
            }
        )
    return changes


def get_working_tree_changes(repo_root: Path) -> list[dict[str, Any]]:
    completed = _run_git(repo_root, "status", "--short")
    if completed is None or completed.returncode != 0:
        return []
    return parse_git_status(completed.stdout)


def get_branch_changed_files(repo_root: Path, base_ref: str = "main") -> list[str]:
    completed = _run_git(repo_root, "diff", "--name-only", f"{base_ref}...HEAD")
    if completed is None or completed.returncode != 0:
        return []
    return [normalize_path(line) for line in completed.stdout.splitlines() if line.strip()]


def build_resolution_candidates(
    working_tree_changes: list[dict[str, Any]],
    branch_changed_files: Iterable[str],
    telemetry_mentions: Counter[str],
) -> list[dict[str, Any]]:
    candidate_map: dict[str, dict[str, Any]] = {}
    branch_changed = {normalize_path(path) for path in branch_changed_files}

    for change in working_tree_changes:
        path = change["path"]
        candidate = candidate_map.setdefault(path, {"path": path, "score": 0, "reasons": []})
        candidate["score"] += 2
        candidate["reasons"].append(f"working_tree:{change['status']}")
        if change["unmerged"]:
            candidate["score"] += 4
            candidate["reasons"].append("unmerged")

    for path in branch_changed:
        candidate = candidate_map.setdefault(path, {"path": path, "score": 0, "reasons": []})
        candidate["score"] += 1
        candidate["reasons"].append("changed_vs_main")

    for path, mentions in telemetry_mentions.items():
        candidate = candidate_map.setdefault(path, {"path": path, "score": 0, "reasons": []})
        candidate["score"] += min(mentions, 3)
        candidate["reasons"].append(f"telemetry_mentions:{mentions}")
        candidate["telemetry_mentions"] = mentions

    ranked = sorted(
        candidate_map.values(),
        key=lambda item: (-item["score"], -int(item.get("telemetry_mentions", 0)), item["path"]),
    )
    return ranked


def build_rework_summary(
    repo_root: Path,
    db_path: Path,
    base_ref: str = "main",
    limit: int = 20,
) -> dict[str, Any]:
    working_tree_changes = get_working_tree_changes(repo_root)
    branch_changed_files = get_branch_changed_files(repo_root, base_ref=base_ref)
    telemetry_mentions = collect_telemetry_file_mentions(db_path)
    resolution_candidates = build_resolution_candidates(
        working_tree_changes,
        branch_changed_files,
        telemetry_mentions,
    )

    top_mentions = [
        {"path": path, "mentions": count}
        for path, count in telemetry_mentions.most_common(limit)
    ]
    return {
        "repo_root": str(repo_root.resolve()),
        "db_path": str(db_path.resolve()),
        "base_ref": base_ref,
        "working_tree_changes": working_tree_changes,
        "branch_changed_files": branch_changed_files,
        "telemetry_hotspots": top_mentions,
        "merge_resolution_candidates": resolution_candidates[:limit],
    }


def write_markdown(summary: dict[str, Any], destination: Path) -> None:
    lines = [
        "# Rework Resolution Summary",
        "",
        f"- Base ref: `{summary['base_ref']}`",
        f"- Working tree changes: {len(summary['working_tree_changes'])}",
        f"- Branch files changed vs base: {len(summary['branch_changed_files'])}",
        f"- Telemetry hotspots: {len(summary['telemetry_hotspots'])}",
        "",
        "## Merge Resolution Candidates",
        "",
    ]

    candidates = summary["merge_resolution_candidates"]
    if not candidates:
        lines.append("- No candidate files detected.")
    else:
        for item in candidates:
            reasons = ", ".join(item["reasons"])
            lines.append(f"- `{item['path']}` (score={item['score']}): {reasons}")

    lines.extend(["", "## Working Tree Changes", ""])
    if not summary["working_tree_changes"]:
        lines.append("- Working tree is clean.")
    else:
        for change in summary["working_tree_changes"]:
            lines.append(f"- `{change['path']}`: `{change['status']}`")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a telemetry-backed rework summary")
    parser.add_argument("--repo-root", default=".", help="Repository root to inspect")
    parser.add_argument("--db", default="telemetry/output/telemetry.db", help="Telemetry SQLite database")
    parser.add_argument("--base-ref", default="main", help="Git base ref used for merge-back summaries")
    parser.add_argument("--limit", type=int, default=20, help="Maximum hotspot/candidate rows")
    parser.add_argument("--json", default="telemetry/output/rework_summary.json", help="JSON output path")
    parser.add_argument("--md", default="telemetry/output/rework_summary.md", help="Markdown output path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    db_path = (repo_root / args.db).resolve() if not Path(args.db).is_absolute() else Path(args.db).resolve()
    json_path = (repo_root / args.json).resolve() if not Path(args.json).is_absolute() else Path(args.json).resolve()
    md_path = (repo_root / args.md).resolve() if not Path(args.md).is_absolute() else Path(args.md).resolve()

    summary = build_rework_summary(
        repo_root=repo_root,
        db_path=db_path,
        base_ref=args.base_ref,
        limit=args.limit,
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary, md_path)

    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
