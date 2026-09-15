#!/usr/bin/env python3
"""Aggregate the last 7 days of activity for the weekly LinkedIn/Substack write-up."""
import datetime
import sys
from pathlib import Path

import collect_claude_code
import collect_cursor
import collect_hermes

DRAFTS_DIR = Path.home() / "learning-log" / "drafts"


def past_week_dates(end_date):
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    return [(end - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]


def build_digest(end_date):
    dates = past_week_dates(end_date)
    sections = []

    tweet_recap = []
    for date in dates:
        draft_file = DRAFTS_DIR / f"{date}.txt"
        if draft_file.exists():
            text = draft_file.read_text().strip()
            if text:
                tweet_recap.append(f"{date}: {text}")
    if tweet_recap:
        sections.append("=== This week's daily tweet recap ===\n" + "\n".join(tweet_recap))

    for date in dates:
        for label, collector in (
            ("Claude Code", collect_claude_code),
            ("Cursor", collect_cursor),
            ("Hermes", collect_hermes),
        ):
            text = collector.collect(date)
            if text:
                sections.append(f"=== {label} sessions on {date} ===\n{text}")

    return "\n\n".join(sections)


def main():
    end_date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().strftime("%Y-%m-%d")
    digest = build_digest(end_date)
    if digest:
        print(digest)


if __name__ == "__main__":
    main()
