#!/usr/bin/env python3
"""Collect a day's Hermes agent activity from ~/.hermes/state.db.

Hermes stores conversation history in a real SQLite schema (messages joined
to sessions on session_id), with a unix-epoch `timestamp` per message and a
`cwd`/`title` per session — much more precise than Cursor's per-tab-only
timestamp.
"""
import datetime
import json
import sqlite3
import sys
from pathlib import Path

MAX_CHARS_PER_SESSION = 20000


def extract_text(content):
    if not content:
        return ""
    if isinstance(content, str):
        stripped = content.strip()
        if stripped.startswith("[") or stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return content
            return extract_text(parsed)
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def collect(date):
    """Return a text digest of Hermes activity for the given YYYY-MM-DD date."""
    db_path = Path.home() / ".hermes" / "state.db"
    if not db_path.exists():
        return ""

    day_start = datetime.datetime.strptime(date, "%Y-%m-%d")
    day_end = day_start + datetime.timedelta(days=1)
    start_ts = day_start.timestamp()
    end_ts = day_end.timestamp()

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT m.session_id, s.cwd, s.title, m.role, m.content, m.timestamp
            FROM messages m
            JOIN sessions s ON s.id = m.session_id
            WHERE m.timestamp >= ? AND m.timestamp < ?
              AND m.role IN ('user', 'assistant')
              AND m.active = 1
            ORDER BY m.session_id, m.timestamp
            """,
            (start_ts, end_ts),
        )
        rows = cur.fetchall()
        conn.close()
    except sqlite3.Error:
        return ""

    if not rows:
        return ""

    by_session = {}
    for session_id, cwd, title, role, content, _ts in rows:
        text = extract_text(content).strip()
        if not text:
            continue
        key = (session_id, title or cwd or "Hermes session")
        by_session.setdefault(key, []).append(f"[{role}] {text}")

    sections = []
    for (session_id, label), entries in by_session.items():
        joined = "\n".join(entries)
        if len(joined) > MAX_CHARS_PER_SESSION:
            joined = "[...earlier truncated]\n" + joined[-MAX_CHARS_PER_SESSION:]
        sections.append(f"## Hermes session: {label}\n{joined}\n")

    return "\n".join(sections)


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else None
    if not date:
        print("usage: collect_hermes.py YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    output = collect(date)
    if output:
        print(output)


if __name__ == "__main__":
    main()
