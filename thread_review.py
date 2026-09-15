"""Telegram review/approval flow for the daily tweet thread — mirrors the
news pipeline's awaiting_review pattern in ~/dev/ai-content/handle_telegram_reply.py.

Imported by ai-content's poller (the single shared Telegram poller) so both
flows share one getUpdates offset instead of racing each other.
"""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "dev" / "ai-content"))
import telegram_lib  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import format_daily_draft  # noqa: E402

DIR = Path(__file__).parent
STATE_FILE = DIR / "state" / "thread_state.json"

APPROVAL_RE = re.compile(
    r"^\s*(approved?|good|great|done|yes|ok(ay)?|lgtm|looks good|👍|perfect|ship it|post it)\s*!?\s*$",
    re.IGNORECASE,
)

# Keyword -> tweet number, for detecting feedback that targets one specific
# tweet (e.g. "for the takeaways, make it punchier") so only that tweet gets
# regenerated instead of the whole thread.
TWEET_LABELS = {
    1: ["progress", "project", " day ", "day 1", "day count", "tweet 1", "tweet one", "first tweet"],
    2: ["process", "tweet 2", "tweet two", "second tweet"],
    3: ["takeaway", "takeaways", "tweet 3", "tweet three", "third tweet", "last tweet"],
}


def detect_target_tweet(feedback):
    """Return the tweet number if feedback clearly targets exactly one tweet,
    else None (ambiguous, multi-target, or generic feedback falls back to a
    full-thread revision)."""
    lowered = f" {feedback.lower()} "
    matched = {n for n, keywords in TWEET_LABELS.items() if any(k in lowered for k in keywords)}
    return matched.pop() if len(matched) == 1 else None


def load_state():
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text())


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


STALE_AFTER = datetime.timedelta(hours=20)


def is_awaiting(state):
    """A state older than STALE_AFTER stops being eligible for routing — an
    abandoned thread from a day ago shouldn't hijack an unrelated reply."""
    if not state or state.get("status") != "awaiting_review":
        return False
    updated_at = state.get("updated_at")
    if not updated_at:
        return True
    age = datetime.datetime.now() - datetime.datetime.fromisoformat(updated_at)
    return age < STALE_AFTER


def send_for_review(date):
    draft_path = Path.home() / "learning-log" / "drafts" / f"{date}.txt"
    draft_text = draft_path.read_text().strip()

    telegram_lib.send_message(
        f"Today's tweet thread — {date}:\n\n{draft_text}\n\n"
        "Reply 'approved' to post it, or send feedback to revise."
    )

    state = {
        "date": date,
        "status": "awaiting_review",
        "draft_path": str(draft_path),
        "revision_count": 0,
        "updated_at": datetime.datetime.now().isoformat(),
    }
    save_state(state)


def get_lessons_block():
    lessons_file = DIR / "voice-lessons.md"
    if lessons_file.exists() and lessons_file.read_text().strip():
        return (
            f"Voice lessons extracted from real posted examples (follow these closely, "
            f"they take priority over generic style guidance below):\n\n"
            f"{lessons_file.read_text().strip()}\n\n"
        )
    return ""


def run_claude_text(prompt):
    result = subprocess.run(
        [
            "claude", "-p", "--no-session-persistence",
            "--disallowedTools", "Write", "Edit", "Bash", "NotebookEdit", "Agent", "WebFetch", "WebSearch",
            "--", prompt,
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def revise_single_tweet(draft_path, target_n, feedback):
    """Revise only tweet `target_n`, leaving every other tweet byte-identical —
    for feedback that clearly targets one section (see detect_target_tweet)."""
    tweets = format_daily_draft.parse(Path(draft_path).read_text())
    if target_n not in tweets:
        return False

    prompt = (
        f"{get_lessons_block()}"
        f"This is one tweet from a thread (the others are staying exactly as they are, "
        f"don't worry about them):\n\n{tweets[target_n]}\n\n"
        f"Feedback on this specific tweet: \"{feedback}\"\n\n"
        "Revise it accordingly. Keep the same label(s) it already starts with. Stay under "
        "280 characters. Match the telegraphic, build-in-public voice (dropped subject "
        "pronouns, no em dashes, no AI-sounding filler). Output ONLY the revised tweet text, "
        "nothing else — no preamble, no delimiter markers."
    )
    revised = run_claude_text(prompt)
    if not revised:
        return False

    tweets[target_n] = format_daily_draft.trim(revised.strip())
    blocks = [f"===TWEET{n}===\n{tweets[n]}" for n in sorted(tweets)]
    Path(draft_path).write_text("\n".join(blocks) + "\n")

    if target_n == 1:
        substack_path = Path(draft_path).parent / f"{Path(draft_path).stem}-substack-note.txt"
        substack_path.write_text(tweets[1] + "\n")

    return True


def revise_draft(draft_path, feedback):
    target_n = detect_target_tweet(feedback)
    if target_n is not None:
        if revise_single_tweet(draft_path, target_n, feedback):
            return True
        # Fall through to full-thread revision if the targeted attempt failed.

    draft_text = Path(draft_path).read_text().strip()
    lessons_block = get_lessons_block()

    current_tweets = format_daily_draft.parse(draft_text)
    current_count = len(current_tweets)

    prompt = (
        f"{lessons_block}"
        f"Here is a {current_count}-tweet Twitter thread draft:\n\n{draft_text}\n\n"
        f"I gave this feedback: \"{feedback}\"\n\n"
        f"Revise it accordingly. The draft currently has {current_count} tweets — KEEP EXACTLY "
        f"{current_count} tweets, preserving every one that the feedback doesn't ask to change, "
        "UNLESS the feedback explicitly asks to add, remove, or merge a tweet (e.g. 'add a tweet "
        "about X', 'drop the takeaways'), in which case follow that instead. Never silently drop "
        "an existing tweet as a side effect of adding a new one — if the feedback asks for an "
        "addition, that means MORE tweets, not a replacement. Keep the first tweet starting with "
        "'Day N' / 'Project: ...' unless told otherwise. Remember the audience: people who want "
        "to build something similar themselves from scratch. These are my own actions and "
        "choices as the builder, not narration of what an AI assistant did.\n\n"
        "Any 'Progress' and 'Process' tweets must be MECE — no overlapping information. Progress "
        "is the WHAT: the goal and what got achieved, as an outcome, no tools or methods. "
        "Process is the HOW: tools/methods/tactical approach used to get there, concrete but "
        "conceptual (not file names or code-level detail), never restating the outcome.\n\n"
        "Telegraphic, build-in-public log style: drop the subject pronoun where natural instead "
        "of writing 'I' (e.g. 'Set up a Telegram bot' not 'I set up a Telegram bot'), use "
        "'I'/'my' sparingly. No em dashes (use periods or commas), no filler like 'it's worth "
        "noting' or 'game-changer', no throat-clearing intros, short direct sentences. Output "
        "each tweet as its own ===TWEETn=== block (===TWEET1===, ===TWEET2===, etc, however many "
        "tweets the result has), each at most 280 characters. No preamble, no commentary outside "
        "the delimited blocks."
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
    format_result = subprocess.run(
        ["python3", str(DIR / "format_daily_draft.py"), str(draft_path)],
        input=result.stdout,
        capture_output=True,
        text=True,
    )
    return format_result.returncode == 0


def handle_reply(state, message):
    if APPROVAL_RE.match(message):
        result = subprocess.run(
            ["python3", str(DIR / "post_tweet.py"), state["draft_path"]],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            telegram_lib.send_message(f"Posted! {result.stdout.strip()}")
            state["status"] = "done"
        else:
            telegram_lib.send_message(f"Posting failed:\n{result.stderr.strip()[-500:]}")
        state["updated_at"] = datetime.datetime.now().isoformat()
        return state

    ok = revise_draft(state["draft_path"], message)
    if not ok:
        telegram_lib.send_message(
            "Couldn't parse a revised draft from that — the original thread is still what "
            "it was. Try rephrasing the feedback, or reply 'approved' to post as-is."
        )
        state["updated_at"] = datetime.datetime.now().isoformat()
        return state

    draft_text = Path(state["draft_path"]).read_text().strip()
    telegram_lib.send_message(
        f"Updated thread:\n\n{draft_text}\n\nReply 'approved' to post, or send more feedback."
    )
    state["revision_count"] = state.get("revision_count", 0) + 1
    state["updated_at"] = datetime.datetime.now().isoformat()
    return state


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "send":
        send_for_review(sys.argv[2])
    else:
        print("usage: thread_review.py send YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
