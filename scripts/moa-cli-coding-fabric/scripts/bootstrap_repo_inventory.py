#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_GITHUB_ROOT = Path(r"C:\Users\eqhsp\Documents\GitHub")
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "repo_inventory.json"

IGNORED_DIRS = {
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
}

LANGUAGE_BY_EXT = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".sh": "shell",
    ".ps1": "powershell",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
}


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


def _detect_default_branch(repo_path: Path) -> str | None:
    code, out = _run(["git", "-C", str(repo_path), "symbolic-ref", "refs/remotes/origin/HEAD"])
    if code != 0 or not out:
        return None
    if "/" in out:
        return out.split("/")[-1]
    return out


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _scan_languages(repo_path: Path, max_files: int) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    scanned = 0
    for base, dirs, files in os.walk(repo_path):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS)
        for file_name in sorted(files):
            scanned += 1
            if scanned > max_files:
                break
            ext = Path(file_name).suffix.lower()
            language = LANGUAGE_BY_EXT.get(ext)
            if language:
                counter[language] += 1
        if scanned > max_files:
            break
    items = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
    return [{"language": lang, "count": count} for lang, count in items[:5]]


def _detect_commands(repo_path: Path) -> tuple[list[str], list[str]]:
    tests: list[str] = []
    builds: list[str] = []

    if (repo_path / "pyproject.toml").exists() or (repo_path / "requirements.txt").exists():
        tests.append("python -m pytest -q")
        builds.append("python -m build")

    pkg = _safe_json(repo_path / "package.json")
    scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}
    has_pnpm = (repo_path / "pnpm-lock.yaml").exists()
    if scripts:
        runner = "pnpm" if has_pnpm else "npm"
        if "test" in scripts:
            tests.append(f"{runner} test")
        if "build" in scripts:
            builds.append(f"{runner} run build")

    if (repo_path / "Cargo.toml").exists():
        tests.append("cargo test")
        builds.append("cargo build")

    if (repo_path / "go.mod").exists():
        tests.append("go test ./...")
        builds.append("go build ./...")

    if (repo_path / "Dockerfile").exists():
        builds.append("docker build -t repo-image .")
    compose_files = ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]
    if any((repo_path / name).exists() for name in compose_files):
        builds.append("docker compose config")

    return _unique(tests), _unique(builds)


def _detect_risk(repo_path: Path) -> str:
    high_markers = [
        repo_path / "k8s",
        repo_path / "helm",
        repo_path / ".github" / "workflows",
    ]
    for marker in high_markers:
        if marker.exists():
            return "high"

    medium_markers = [
        repo_path / "Dockerfile",
        repo_path / "docker-compose.yml",
        repo_path / "docker-compose.yaml",
        repo_path / "terraform",
        repo_path / "infra",
    ]
    for marker in medium_markers:
        if marker.exists():
            return "medium"
    return "low"


def _discover_repos(root: Path) -> list[Path]:
    repos: list[Path] = []
    if not root.exists():
        return repos

    seen: set[str] = set()
    skip = set(IGNORED_DIRS) | {"backups"}
    for current, dirs, _ in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        current_path = Path(current)
        dot_git = current_path / ".git"
        if not dot_git.exists():
            continue
        canonical = str(current_path.resolve()).lower()
        if canonical in seen:
            continue
        seen.add(canonical)
        repos.append(current_path)

    return sorted(repos, key=lambda p: str(p).lower())


def build_inventory(root: Path, max_files: int) -> dict[str, Any]:
    repos = _discover_repos(root)
    records: list[dict[str, Any]] = []
    for repo in repos:
        tests, builds = _detect_commands(repo)
        record = {
            "name": repo.name,
            "path": str(repo.resolve()),
            "is_git_repo": (repo / ".git").exists(),
            "default_branch": _detect_default_branch(repo),
            "languages": _scan_languages(repo, max_files=max_files),
            "recommended_test_commands": tests,
            "recommended_build_commands": builds,
            "risk_profile": _detect_risk(repo),
        }
        records.append(record)

    return {
        "schema_version": "1",
        "root": str(root.resolve()),
        "ignored_dirs": sorted(IGNORED_DIRS),
        "repos": records,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic Codex repo inventory.")
    parser.add_argument("--root", default=str(DEFAULT_GITHUB_ROOT), help="Root folder of local repositories.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path.")
    parser.add_argument("--max-files-per-repo", type=int, default=4000, help="Max scanned files per repo.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    inventory = build_inventory(root=root, max_files=max(200, int(args.max_files_per_repo)))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"wrote: {output}")
    print(f"repos: {len(inventory['repos'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
