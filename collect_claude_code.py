#!/usr/bin/env python3
"""Collect a day's Claude Code session activity from ~/.claude/projects/*/*.jsonl."""
import datetime
import json
import sys
from pathlib import Path

MAX_CHARS_PER_PROJECT = 20000


def local_date(timestamp):
    """Convert a UTC ISO8601 timestamp (e.g. '2026-09-06T00:00:07.725Z') to a
    local YYYY-MM-DD date string. Records are stored in UTC, so naive string
    prefix matching against a local date misattributes evening activity (in
    US timezones) to the wrong calendar day."""
    if not timestamp:
        return None
    try:
        dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone().strftime("%Y-%m-%d")


def extract_text(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return ""


def collect(date):
    """Return a text digest of Claude Code activity for the given YYYY-MM-DD date."""
    projects_dir = Path.home() / ".claude" / "projects"
    by_project = {}

    for jsonl_file in projects_dir.glob("*/*.jsonl"):
        try:
            with jsonl_file.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record.get("type") not in ("user", "assistant"):
                        continue
                    if local_date(record.get("timestamp")) != date:
                        continue
                    message = record.get("message") or {}
                    text = extract_text(message).strip()
                    if not text:
                        continue
                    cwd = record.get("cwd", "unknown project")
                    role = message.get("role", record.get("type"))
                    by_project.setdefault(cwd, []).append(f"[{role}] {text}")
        except (OSError, IOError):
            continue

    if not by_project:
        return ""

    sections = []
    for cwd, entries in by_project.items():
        joined = "\n".join(entries)
        if len(joined) > MAX_CHARS_PER_PROJECT:
            # Keep the tail, not the head — late-session content (fixes, final
            # state, what actually shipped) matters more than early exploration,
            # and truncating from the head silently lost real shipped work before.
            joined = "[...earlier truncated]\n" + joined[-MAX_CHARS_PER_PROJECT:]
        sections.append(f"## Project: {cwd}\n{joined}\n")

    return "\n".join(sections)


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else None
    if not date:
        print("usage: collect_claude_code.py YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    output = collect(date)
    if output:
        print(output)


if __name__ == "__main__":
    main()
