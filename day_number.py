#!/usr/bin/env python3
"""Track and print the running "Day N" counter for the content-system thread.

Day 1 is whichever calendar date this first runs. Day N thereafter is just
elapsed calendar days since then (+1) — so a day with no thread doesn't need
special handling, it just shows up as a gap (Day 5, then Day 7) rather than
needing a separate "posts made" counter.
"""
import datetime
import sys
from pathlib import Path

DAY_ZERO_FILE = Path(__file__).parent / "state" / "day_zero.txt"


def day_number(for_date=None):
    for_date = for_date or datetime.date.today()

    DAY_ZERO_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DAY_ZERO_FILE.exists():
        day_zero = datetime.date.fromisoformat(DAY_ZERO_FILE.read_text().strip())
    else:
        day_zero = for_date
        DAY_ZERO_FILE.write_text(day_zero.isoformat())

    return (for_date - day_zero).days + 1


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    d = datetime.date.fromisoformat(date_arg) if date_arg else None
    print(day_number(d))
