#!/usr/bin/env python3
"""Capture a posted tweet thread into the golden set, and update the running
voice-lessons doc with what it teaches about tone/style/voice.

Called automatically by post_tweet.py after every successful post — closes
the loop so every posted thread (currently: everything posted during
manual-writing mode) informs future generation. Skips re-extraction if this
exact date was already captured with identical content, so re-posting or
re-running doesn't duplicate lesson entries.
"""
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).parent
GOLDEN_SET_DIR = DIR / "golden-set"
LESSONS_FILE = DIR / "voice-lessons.md"

LESSONS_HEADER = """# Voice Lessons from the Golden Set

Running notes on tone, style, and voice, extracted from posted tweets/threads.
Auto-updated after every post by capture_golden_example.py. Feed this into
run_daily.sh / thread_review.py's prompts to keep generation matched to
actual voice. Each entry cites which example it came from.
"""


def capture(date, example_text):
    GOLDEN_SET_DIR.mkdir(parents=True, exist_ok=True)
    golden_path = GOLDEN_SET_DIR / f"{date}.txt"

    if golden_path.exists() and golden_path.read_text().strip() == example_text.strip():
        return None  # already captured, nothing changed

    golden_path.write_text(example_text.strip() + "\n")

    existing_lessons = LESSONS_FILE.read_text() if LESSONS_FILE.exists() else LESSONS_HEADER

    prompt = (
        f"Here is the current running voice-lessons doc:\n\n{existing_lessons}\n\n"
        f"Here is a new posted example (from {date}), a real tweet thread that future "
        f"automated drafts should sound like:\n\n{example_text}\n\n"
        "Extend the doc with new concrete, specific observations about tone/style/voice "
        "from this example: word choice, sentence structure, what gets described vs left "
        "out, personality/humor, level of detail, formatting quirks (e.g. fragments vs full "
        "sentences, singular vs plural labels), anything a prompt-writer could turn into a "
        "concrete instruction. Don't repeat lessons already in the doc — either add genuinely "
        "new ones under a new dated section, or refine an existing lesson if this example "
        "clarifies or contradicts it (note the conflict explicitly if so). Keep the header "
        "and existing dated sections intact. Output ONLY the raw FULL updated markdown doc "
        "as plain text — no code fence wrapper, no preamble, no commentary about what you did."
    )

    result = subprocess.run(
        [
            "claude", "-p", "--no-session-persistence",
            "--disallowedTools", "Write", "Edit", "Bash", "NotebookEdit", "Agent", "WebFetch", "WebSearch",
            "--", prompt,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"Lesson extraction failed: {result.stderr.strip()[-500:]}")

    LESSONS_FILE.write_text(result.stdout.strip() + "\n")
    return golden_path


def main():
    if len(sys.argv) != 2:
        print("usage: capture_golden_example.py YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    date = sys.argv[1]
    draft_path = Path.home() / "learning-log" / "drafts" / f"{date}.txt"
    if not draft_path.exists():
        print(f"No draft found at {draft_path}", file=sys.stderr)
        sys.exit(1)

    try:
        golden_path = capture(date, draft_path.read_text())
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if golden_path is None:
        print(f"{date} already captured, no change.")
    else:
        print(f"Captured {golden_path}, updated {LESSONS_FILE}")


if __name__ == "__main__":
    main()
