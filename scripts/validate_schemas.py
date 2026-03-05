"""Validate JSON payloads against contract schemas."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator


SCHEMA_MAP = {
    "AxQxOS/TaskReceipt/v1": "task-receipt.v1.schema.json",
    "AxQxOS/PipelineEvent/v1": "pipeline-event.v1.schema.json",
    "AxQxOS/WebhookEnvelope/v1": "webhook-envelope.v1.schema.json",
    "AxQxOS/AntigravitySession/v1": "antigravity-session.v1.schema.json",
    "AxQxOS/LoRAReceipt/v1": "lora-receipt.v1.schema.json",
    "AxQxOS/YieldCurveReceipt/v1": "yield-curve-receipt.v1.schema.json",
}


def infer_schema_id(payload: dict) -> str | None:
    schema_id = payload.get("schema")
    if schema_id:
        return schema_id
    if payload.get("event") == "pipeline.complete":
        return "AxQxOS/PipelineEvent/v1"
    if payload.get("envelope_version") == "1.0":
        return "AxQxOS/WebhookEnvelope/v1"
    return None


def load_schema(schemas_dir: Path, schema_name: str) -> dict:
    return json.loads((schemas_dir / schema_name).read_text(encoding="utf-8"))


def validate_file(path: Path, schemas_dir: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))

    schema_id = infer_schema_id(payload)
    if not schema_id:
        raise ValueError(f"{path}: missing schema field")
    if schema_id not in SCHEMA_MAP:
        raise ValueError(f"{path}: unsupported schema '{schema_id}'")

    schema = load_schema(schemas_dir, SCHEMA_MAP[schema_id])
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        raise ValueError(f"{path}: {errors[0].message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate AxQxOS contract JSON files")
    parser.add_argument("paths", nargs="+", help="Files or directories to validate")
    parser.add_argument("--schemas-dir", default="schemas/contracts", help="Schema directory")
    args = parser.parse_args()

    schemas_dir = Path(args.schemas_dir)
    files: list[Path] = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.json")))
        elif p.suffix == ".json":
            files.append(p)

    failures = []
    for f in files:
        try:
            validate_file(f, schemas_dir)
        except Exception as exc:
            failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        raise SystemExit(1)

    print(f"Validated {len(files)} file(s)")


if __name__ == "__main__":
    main()
