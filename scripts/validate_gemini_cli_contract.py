#!/usr/bin/env python3
"""Validate the repo copy of the Gemini CLI artifact template."""

from __future__ import annotations

import json
from pathlib import Path
import sys


REQUIRED_TOP_LEVEL = {
    "template_version",
    "skill_name",
    "runtime",
    "chain_strategy",
    "request",
    "context",
    "artifacts",
}
REQUIRED_RUNTIME = {"tool", "command", "install"}
REQUIRED_REQUEST = {"model", "approval_mode", "output_format"}
REQUIRED_ARTIFACT = {"id", "path", "kind"}


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return fail("usage: validate_gemini_cli_contract.py <template-path>")

    template_path = Path(argv[1]).resolve()
    if not template_path.is_file():
        return fail(f"template not found: {template_path}")

    with template_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    missing = REQUIRED_TOP_LEVEL - payload.keys()
    if missing:
        return fail(f"missing top-level keys: {sorted(missing)}")

    runtime = payload["runtime"]
    missing_runtime = REQUIRED_RUNTIME - runtime.keys()
    if missing_runtime:
        return fail(f"missing runtime keys: {sorted(missing_runtime)}")
    if runtime["command"] != "gemini":
        return fail("runtime.command must be 'gemini'")

    request = payload["request"]
    missing_request = REQUIRED_REQUEST - request.keys()
    if missing_request:
        return fail(f"missing request keys: {sorted(missing_request)}")
    if request["approval_mode"] not in {"default", "auto_edit", "yolo", "plan"}:
        return fail("request.approval_mode is invalid")
    if request["output_format"] not in {"json", "text", "stream-json"}:
        return fail("request.output_format is invalid")

    if payload["chain_strategy"] != "dot_product":
        return fail("chain_strategy must be 'dot_product'")

    artifacts = payload["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        return fail("artifacts must be a non-empty list")

    for index, artifact in enumerate(artifacts):
        missing_artifact = REQUIRED_ARTIFACT - artifact.keys()
        if missing_artifact:
            return fail(f"artifact[{index}] missing keys: {sorted(missing_artifact)}")

    print(f"OK: Gemini CLI artifact template validated at {template_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
