"""Ingest AxQxOS/WHAM JSONL telemetry into normalized SQLite tables."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Event:
    source_file: str
    source_kind: str
    event_type: str
    session_id: str | None
    event_timestamp: str | None
    event_uuid: str | None
    parent_uuid: str | None
    agent_id: str | None
    payload_json: str

    @property
    def event_key(self) -> str:
        parts = [
            self.session_id or "",
            self.event_timestamp or "",
            self.event_uuid or "",
            self.source_file,
            self.payload_json,
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def default_sources(root: Path) -> list[Path]:
    return [
        root / "c--Users-eqhsp--antigravity-A2A-MCP-A2A-MCP",
        root / "c--Users-eqhsp-Documents-GitHub-A2A-MCP",
    ]


def find_jsonl_files(paths: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if not p.exists():
            continue
        if p.is_file() and p.suffix == ".jsonl":
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.jsonl")))
    return files


def classify_source(path: Path) -> str:
    p = path.as_posix().lower()
    if "/subagents/" in p:
        return "subagent"
    return "session"


def parse_event(path: Path, line: str, line_no: int) -> Event | None:
    line = line.strip()
    if not line:
        return None

    payload = json.loads(line)
    event_type = str(payload.get("type") or payload.get("message", {}).get("role") or "unknown")

    session_id = payload.get("sessionId")
    event_timestamp = payload.get("timestamp")
    event_uuid = payload.get("uuid")
    parent_uuid = payload.get("parentUuid")
    agent_id = payload.get("agentId")

    # Map some nested message IDs as fallback identifiers
    if not event_uuid:
        msg = payload.get("message", {})
        event_uuid = msg.get("id")

    if not event_uuid:
        event_uuid = f"{path.name}:{line_no}"

    return Event(
        source_file=str(path),
        source_kind=classify_source(path),
        event_type=event_type,
        session_id=session_id,
        event_timestamp=event_timestamp,
        event_uuid=event_uuid,
        parent_uuid=parent_uuid,
        agent_id=agent_id,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS session_events (
          event_key TEXT PRIMARY KEY,
          source_file TEXT NOT NULL,
          source_kind TEXT NOT NULL,
          event_type TEXT NOT NULL,
          session_id TEXT,
          event_timestamp TEXT,
          event_uuid TEXT,
          parent_uuid TEXT,
          payload_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE IF NOT EXISTS agent_events (
          event_key TEXT PRIMARY KEY,
          session_id TEXT,
          agent_id TEXT,
          event_type TEXT NOT NULL,
          event_timestamp TEXT,
          event_uuid TEXT,
          payload_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE IF NOT EXISTS tool_events (
          event_key TEXT PRIMARY KEY,
          session_id TEXT,
          event_timestamp TEXT,
          event_uuid TEXT,
          tool_name TEXT,
          operation TEXT,
          payload_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE TABLE IF NOT EXISTS pipeline_receipts (
          event_key TEXT PRIMARY KEY,
          session_id TEXT,
          event_timestamp TEXT,
          event_uuid TEXT,
          schema_id TEXT,
          status TEXT,
          payload_json TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );

        CREATE INDEX IF NOT EXISTS idx_session_events_session_time
          ON session_events(session_id, event_timestamp);

        CREATE INDEX IF NOT EXISTS idx_agent_events_session_time
          ON agent_events(session_id, event_timestamp);

        CREATE INDEX IF NOT EXISTS idx_tool_events_session_time
          ON tool_events(session_id, event_timestamp);

        CREATE INDEX IF NOT EXISTS idx_pipeline_receipts_schema_time
          ON pipeline_receipts(schema_id, event_timestamp);
        """
    )


def ingest_file(conn: sqlite3.Connection, path: Path) -> tuple[int, int]:
    inserted = 0
    skipped = 0

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, start=1):
            try:
                event = parse_event(path, line, line_no)
                if event is None:
                    continue

                conn.execute(
                    """
                    INSERT OR IGNORE INTO session_events (
                      event_key, source_file, source_kind, event_type, session_id,
                      event_timestamp, event_uuid, parent_uuid, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_key,
                        event.source_file,
                        event.source_kind,
                        event.event_type,
                        event.session_id,
                        event.event_timestamp,
                        event.event_uuid,
                        event.parent_uuid,
                        event.payload_json,
                    ),
                )

                if conn.total_changes > inserted:
                    inserted += 1
                else:
                    skipped += 1

                payload = json.loads(event.payload_json)

                if event.agent_id or event.source_kind == "subagent":
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO agent_events (
                          event_key, session_id, agent_id, event_type, event_timestamp,
                          event_uuid, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event.event_key,
                            event.session_id,
                            event.agent_id,
                            event.event_type,
                            event.event_timestamp,
                            event.event_uuid,
                            event.payload_json,
                        ),
                    )

                message = payload.get("message", {})
                has_tool_event = payload.get("type") == "queue-operation" or "tool" in json.dumps(message)
                if has_tool_event:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO tool_events (
                          event_key, session_id, event_timestamp, event_uuid,
                          tool_name, operation, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event.event_key,
                            event.session_id,
                            event.event_timestamp,
                            event.event_uuid,
                            payload.get("name") or message.get("name"),
                            payload.get("operation"),
                            event.payload_json,
                        ),
                    )

                schema_id = payload.get("schema")
                if schema_id or payload.get("canonical"):
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO pipeline_receipts (
                          event_key, session_id, event_timestamp, event_uuid,
                          schema_id, status, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event.event_key,
                            event.session_id,
                            event.event_timestamp,
                            event.event_uuid,
                            schema_id,
                            payload.get("status"),
                            event.payload_json,
                        ),
                    )

            except Exception:
                skipped += 1

    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest AxQxOS telemetry JSONL files")
    parser.add_argument("--root", default=".", help="Repo root")
    parser.add_argument(
        "--sources",
        nargs="*",
        help="Optional source paths (defaults to known JSONL roots)",
    )
    parser.add_argument("--db", default="telemetry/output/telemetry.db", help="SQLite output path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    db_path = (root / args.db).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    source_paths = [Path(p).resolve() for p in args.sources] if args.sources else default_sources(root)
    files = find_jsonl_files(source_paths)

    conn = sqlite3.connect(str(db_path))
    init_db(conn)

    total_inserted = 0
    total_skipped = 0
    for file_path in files:
        inserted, skipped = ingest_file(conn, file_path)
        total_inserted += inserted
        total_skipped += skipped

    conn.commit()
    conn.close()

    print(f"Files: {len(files)}")
    print(f"Inserted: {total_inserted}")
    print(f"Skipped: {total_skipped}")
    print(f"DB: {db_path}")


if __name__ == "__main__":
    main()
