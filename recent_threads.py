#!/usr/bin/env python3
"""Print the last few days' tweet threads, for feeding into today's draft
prompt as continuity context — so the model knows what's already been said
and doesn't repeat itself or lose the narrative thread.
"""
import datetime
import sys
from pathlib import Path

DRAFTS_DIR = Path.home() / "learning-log" / "drafts"
LOOKBACK_DAYS = 5


def main():
    today = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().strftime("%Y-%m-%d")

    entries = []
    for f in sorted(DRAFTS_DIR.glob("*.txt")):
        if f.stem == today or "-substack-note" in f.name or ".raw." in f.name:
            continue
        entries.append(f)

    entries = entries[-LOOKBACK_DAYS:]
    if not entries:
        return

    for f in entries:
        print(f"--- {f.stem} ---")
        print(f.read_text().strip())
        print()


if __name__ == "__main__":
    main()
