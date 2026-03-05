"""Manage git safe.directory entries for discovered repositories under a root path."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Iterable

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


def _run(cmd: list[str]) -> tuple[int, str]:
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
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
        canonical = str(path.resolve()).lower()
        if canonical in seen:
            continue
        seen.add(canonical)
        repos.append(path.resolve())
    return sorted(repos, key=lambda p: str(p).lower())


def get_safe_directories() -> list[Path]:
    code, output = _run(["git", "config", "--global", "--get-all", "safe.directory"])
    if code != 0 or not output:
        return []
    out: list[Path] = []
    for line in output.splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            out.append(Path(text).resolve())
        except OSError:
            continue
    return out


def _normalized(paths: Iterable[Path]) -> dict[str, Path]:
    return {str(path.resolve()).lower(): path.resolve() for path in paths}


def apply_changes(to_add: list[Path], to_remove: list[Path]) -> None:
    for path in to_remove:
        _run(["git", "config", "--global", "--unset-all", "safe.directory", str(path)])
    for path in to_add:
        _run(["git", "config", "--global", "--add", "safe.directory", str(path)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Root directory to scan for git repos.")
    parser.add_argument("--output-json", help="Optional output report path.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not apply git config changes.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Root not found: {root}")

    discovered = discover_repos(root)
    existing = get_safe_directories()

    discovered_map = _normalized(discovered)
    existing_map = _normalized(existing)
    root_prefix = str(root).lower()

    to_add = [path for key, path in sorted(discovered_map.items()) if key not in existing_map]
    to_remove = [
        path
        for key, path in sorted(existing_map.items())
        if key.startswith(root_prefix) and key not in discovered_map
    ]

    if not args.dry_run:
        apply_changes(to_add=to_add, to_remove=to_remove)

    report = {
        "root": str(root),
        "dry_run": bool(args.dry_run),
        "discovered_repos": [str(x) for x in discovered],
        "to_add": [str(x) for x in to_add],
        "to_remove": [str(x) for x in to_remove],
        "counts": {
            "discovered": len(discovered),
            "to_add": len(to_add),
            "to_remove": len(to_remove),
        },
    }

    if args.output_json:
        out = Path(args.output_json).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
