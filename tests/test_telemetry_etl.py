"""Idempotency test for JSONL telemetry ingestion."""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "telemetry/output/test_telemetry.db"


def _count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_ingestion_is_idempotent() -> None:
    if DB.exists():
        DB.unlink()

    cmd = [
        sys.executable,
        str(ROOT / "telemetry/etl.py"),
        "--root",
        str(ROOT),
        "--db",
        str(DB),
    ]
    subprocess.run(cmd, check=True)

    conn = sqlite3.connect(str(DB))
    first_count = _count(conn, "session_events")
    conn.close()

    subprocess.run(cmd, check=True)

    conn = sqlite3.connect(str(DB))
    second_count = _count(conn, "session_events")
    conn.close()

    assert first_count == second_count
    assert first_count > 0
