#!/usr/bin/env python3
"""Parse claude's raw tweet-thread output into a clean, delimited thread
draft file.

Expects raw text on stdin containing one or more tweets, each preceded by
its own delimiter line (===TWEET1===, ===TWEET2===, ...) — normally 3, but
any count is supported (e.g. a revision that adds a tweet). Each tweet's
full text (which may itself span multiple lines/paragraphs) is trimmed to
fit 280 characters as a safety net, then written back out in the same
delimited format to the given output path. Tweet 1's text alone is also
written to a sibling "-substack-note.txt" file for manual posting as a
Substack Note.
"""
import re
import sys
from pathlib import Path

DELIMITER_RE = re.compile(r"^===TWEET(\d)===\s*$")
MAX_CHARS = 280


def parse(text):
    tweets = {}
    current = None
    buffer = []
    for line in text.splitlines():
        m = DELIMITER_RE.match(line.strip())
        if m:
            if current is not None:
                tweets[current] = "\n".join(buffer).strip()
            current = int(m.group(1))
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        tweets[current] = "\n".join(buffer).strip()
    return tweets


def trim(text):
    if len(text) > MAX_CHARS:
        return text[: MAX_CHARS - 3] + "..."
    return text


def main():
    if len(sys.argv) != 2:
        print("usage: format_daily_draft.py OUTPUT_PATH  (reads raw text on stdin)", file=sys.stderr)
        sys.exit(1)

    output_path = Path(sys.argv[1])
    raw = sys.stdin.read()
    tweets = parse(raw)

    if not tweets or not all(tweets.values()):
        empty = [n for n, t in tweets.items() if not t]
        raw_path = output_path.with_suffix(output_path.suffix + ".raw.txt")
        raw_path.write_text(raw)
        print(
            f"Could not parse a usable draft from claude's output (found {len(tweets)} tweet(s), "
            f"empty: {empty}). Raw output saved to {raw_path} for debugging.",
            file=sys.stderr,
        )
        sys.exit(1)

    numbers = sorted(tweets)
    if numbers != list(range(1, len(numbers) + 1)):
        raw_path = output_path.with_suffix(output_path.suffix + ".raw.txt")
        raw_path.write_text(raw)
        print(
            f"Tweet numbers aren't consecutive starting at 1, got {numbers}. "
            f"Raw output saved to {raw_path} for debugging.",
            file=sys.stderr,
        )
        sys.exit(1)

    blocks = [f"===TWEET{n}===\n{trim(tweets[n])}" for n in numbers]
    output_path.write_text("\n".join(blocks) + "\n")

    substack_path = output_path.parent / f"{output_path.stem}-substack-note.txt"
    substack_path.write_text(trim(tweets[1]) + "\n")


if __name__ == "__main__":
    main()
