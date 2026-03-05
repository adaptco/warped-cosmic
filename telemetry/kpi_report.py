"""Generate KPI snapshots from telemetry SQLite database."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def q1(conn: sqlite3.Connection, sql: str) -> int:
    row = conn.execute(sql).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def build_kpis(conn: sqlite3.Connection) -> dict:
    sessions = q1(conn, "SELECT COUNT(DISTINCT session_id) FROM session_events WHERE session_id IS NOT NULL")
    total_events = q1(conn, "SELECT COUNT(*) FROM session_events")
    subagent_events = q1(conn, "SELECT COUNT(*) FROM session_events WHERE source_kind='subagent'")
    tool_events = q1(conn, "SELECT COUNT(*) FROM tool_events")
    receipts = q1(conn, "SELECT COUNT(*) FROM pipeline_receipts")

    top_types = conn.execute(
        """
        SELECT event_type, COUNT(*) AS c
        FROM session_events
        GROUP BY event_type
        ORDER BY c DESC
        LIMIT 10
        """
    ).fetchall()

    return {
        "sessions": sessions,
        "total_events": total_events,
        "subagent_events": subagent_events,
        "tool_events": tool_events,
        "pipeline_receipts": receipts,
        "top_event_types": [{"event_type": r[0], "count": int(r[1])} for r in top_types],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate telemetry KPI artifacts")
    parser.add_argument("--db", default="telemetry/output/telemetry.db")
    parser.add_argument("--json", default="telemetry/output/kpi.json")
    parser.add_argument("--md", default="telemetry/output/kpi.md")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB does not exist: {db_path}")

    conn = sqlite3.connect(str(db_path))
    kpis = build_kpis(conn)
    conn.close()

    json_path = Path(args.json)
    md_path = Path(args.md)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(kpis, indent=2), encoding="utf-8")

    lines = [
        "# Telemetry KPI Snapshot",
        "",
        f"- Sessions: {kpis['sessions']}",
        f"- Total events: {kpis['total_events']}",
        f"- Subagent events: {kpis['subagent_events']}",
        f"- Tool events: {kpis['tool_events']}",
        f"- Pipeline receipts: {kpis['pipeline_receipts']}",
        "",
        "## Top Event Types",
        "",
    ]
    for row in kpis["top_event_types"]:
        lines.append(f"- `{row['event_type']}`: {row['count']}")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
