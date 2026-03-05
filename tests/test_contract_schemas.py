"""Contract schema tests for core payload types."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas/contracts"


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_task_receipt_schema() -> None:
    payload = {
        "schema": "AxQxOS/TaskReceipt/v1",
        "taskId": "task-123",
        "requestingAgent": "WEBHOOK",
        "targetRole": "AVATAR_CODEGEN",
        "format": "json",
        "status": "PENDING",
        "createdAt": "2026-03-05T00:00:00Z",
    }
    Draft202012Validator(_schema("task-receipt.v1.schema.json")).validate(payload)


def test_pipeline_event_schema() -> None:
    payload = {
        "event": "pipeline.complete",
        "status": "success",
        "sha": "abc123",
        "capsule": "Sol.F1",
        "canonical": "Canonical truth, attested and replayable.",
    }
    Draft202012Validator(_schema("pipeline-event.v1.schema.json")).validate(payload)


def test_webhook_envelope_schema() -> None:
    payload = {
        "envelope_version": "1.0",
        "task_id": "T-001",
        "from_agent": "Echo",
        "to_agent": "Dot",
        "payload": {"artifact_id": "artifact:1", "data": {"ok": True}},
        "timestamp": "2026-03-05T00:00:00Z",
    }
    Draft202012Validator(_schema("webhook-envelope.v1.schema.json")).validate(payload)
