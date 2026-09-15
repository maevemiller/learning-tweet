#!/usr/bin/env python3
"""Collect a day's Cursor AI chat activity — both regular local chat
(workspaceStorage state.vscdb) and Background Composer / cloud-agent
sessions (globalStorage conversation-search.db), which store transcripts in
a completely different place and don't show up in the per-workspace chat
key at all. Found 2026-09-14 when a real day of background-composer
activity was silently missing from the daily thread.

Cursor has no per-message timestamp in the regular chat data, only a
per-tab `lastSendTime`. So a tab is included if it was last touched on the
given date; this is an approximation (a tab active across midnight could
pull in a little of the adjacent day too), not a hard per-message filter.
The background-composer index does have a real per-conversation
`updated_at` timestamp, so that source is filtered precisely.
"""
import datetime
import json
import sqlite3
import sys
from pathlib import Path

MAX_CHARS_PER_TAB = 20000
CHAT_KEY = "workbench.panel.aichat.view.aichat.chatdata"
CONVERSATION_SEARCH_DB = (
    Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "conversation-search.db"
)


def date_from_epoch_ms(epoch_ms):
    try:
        return datetime.datetime.fromtimestamp(epoch_ms / 1000).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return None


def collect_background_composer(date):
    """Return a text digest of Background Composer / cloud-agent Cursor
    sessions updated on the given YYYY-MM-DD date, from the global
    conversation-search index (covers sessions the per-workspace chat key
    never sees at all, since those run remotely)."""
    if not CONVERSATION_SEARCH_DB.exists():
        return []

    day_start = datetime.datetime.strptime(date, "%Y-%m-%d")
    day_end = day_start + datetime.timedelta(days=1)
    start_ms = int(day_start.timestamp() * 1000)
    end_ms = int(day_end.timestamp() * 1000)

    try:
        conn = sqlite3.connect(f"file:{CONVERSATION_SEARCH_DB}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT fts_rowid, title FROM conversations WHERE updated_at >= ? AND updated_at < ?",
            (start_ms, end_ms),
        )
        rows = cur.fetchall()
        sections = []
        for fts_rowid, title in rows:
            cur.execute("SELECT body FROM conversation_fts WHERE rowid = ?", (fts_rowid,))
            body_row = cur.fetchone()
            body = (body_row[0] if body_row else "").strip()
            if not body:
                continue
            if len(body) > MAX_CHARS_PER_TAB:
                body = "[...earlier truncated]\n" + body[-MAX_CHARS_PER_TAB:]
            sections.append(f"## Cursor background composer: {title}\n{body}\n")
        conn.close()
        return sections
    except sqlite3.Error:
        return []


def collect(date):
    """Return a text digest of Cursor chat activity for the given YYYY-MM-DD date."""
    sections = collect_background_composer(date)

    storage_root = Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage"
    if not storage_root.exists():
        return "\n".join(sections)

    for db_path in storage_root.glob("*/state.vscdb"):
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT value FROM ItemTable WHERE key = ?", (CHAT_KEY,))
            row = cur.fetchone()
            conn.close()
        except sqlite3.Error:
            continue

        if not row:
            continue

        try:
            data = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            continue

        for tab in data.get("tabs", []):
            if date_from_epoch_ms(tab.get("lastSendTime")) != date:
                continue
            bubbles = tab.get("bubbles", [])
            entries = []
            for bubble in bubbles:
                text = (bubble.get("text") or "").strip()
                if not text:
                    continue
                role = bubble.get("type", "?")
                entries.append(f"[{role}] {text}")
            if not entries:
                continue
            title = tab.get("chatTitle") or "Untitled chat"
            joined = "\n".join(entries)
            if len(joined) > MAX_CHARS_PER_TAB:
                joined = "[...earlier truncated]\n" + joined[-MAX_CHARS_PER_TAB:]
            sections.append(f"## Cursor chat: {title}\n{joined}\n")

    return "\n".join(sections)


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else None
    if not date:
        print("usage: collect_cursor.py YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    output = collect(date)
    if output:
        print(output)


if __name__ == "__main__":
    main()
