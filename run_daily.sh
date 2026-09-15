#!/bin/bash
set -euo pipefail

# launchd runs jobs with a minimal PATH that doesn't include where the
# standalone claude CLI lives (installed via `npm install -g`).
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATE="$(date +%Y-%m-%d)"

NOTES_DIR="$HOME/learning-log/notes"
DRAFTS_DIR="$HOME/learning-log/drafts"
mkdir -p "$NOTES_DIR" "$DRAFTS_DIR"

NOTES_FILE="$NOTES_DIR/$DATE.md"
touch "$NOTES_FILE"

TODAY_FILE="$(mktemp)"
CONTEXT_FILE="$(mktemp)"
trap 'rm -f "$TODAY_FILE" "$CONTEXT_FILE"' EXIT

{
  echo "=== Claude Code sessions today ($DATE) ==="
  python3 "$DIR/collect_claude_code.py" "$DATE"
  echo
  echo "=== Cursor sessions today ($DATE) ==="
  python3 "$DIR/collect_cursor.py" "$DATE"
  echo
  echo "=== Hermes sessions today ($DATE) ==="
  python3 "$DIR/collect_hermes.py" "$DATE"
  echo
  echo "=== Manual notes today ==="
  cat "$NOTES_FILE"
} > "$TODAY_FILE"

# Strip section headers/blank lines to check if there's any real content
# TODAY — deliberately checked before the recent-threads context is added,
# so a quiet day doesn't produce a tweet made purely of recycled history.
CONTENT_CHARS=$(grep -v '^===' "$TODAY_FILE" | grep -v '^##' | tr -d '[:space:]' | wc -c | tr -d ' ')

if [ "$CONTENT_CHARS" -lt 20 ]; then
  osascript -e "display notification \"No learning activity found for $DATE — nothing to tweet.\" with title \"Daily Learning Tweet\""
  exit 0
fi

{
  if [ -s "$DIR/voice-lessons.md" ]; then
    echo "=== Voice lessons (extracted from real posted examples — follow these closely) ==="
    cat "$DIR/voice-lessons.md"
    echo
  fi
  echo "=== Recent daily threads (for continuity — don't repeat these, build on them) ==="
  python3 "$DIR/recent_threads.py" "$DATE"
  cat "$TODAY_FILE"
} > "$CONTEXT_FILE"

DRAFT_FILE="$DRAFTS_DIR/$DATE.txt"
DAY_NUMBER="$(python3 "$DIR/day_number.py" "$DATE")"

PROMPT="You are drafting a 3-tweet Twitter thread about my content-system/side-project progress today. Base it ONLY on the material piped to you below (recent threads for context, plus today's actual activity) — do not invent details. No hashtags, no emoji spam.

AUDIENCE AND VOICE: this is for people who want to build something similar themselves, starting from scratch. These are my own actions and choices as the builder — never narrate what an AI assistant/tool did on my behalf, even though I used one.

WRITING STYLE: telegraphic, build-in-public log style. Drop the subject pronoun where natural instead of writing 'I' — start sentences with the verb ('Set up an X Developer account', 'Test-drove Hermes to auto-research', 'Rough pipeline underway') rather than 'I set up' or 'I tested'. Use 'I'/'my' sparingly, only where dropping it would be confusing. Sound like a real person jotting notes, not an AI. No em dashes — use periods or commas instead. No filler like 'it's worth noting', 'game-changer', 'seamless', 'leverage', 'dive into', 'at the end of the day'. No throat-clearing intros. Short, direct, plain sentences. Cut any word that isn't doing work. If the material below includes a 'Voice lessons' section, those are extracted from real posted examples and take priority over this generic guidance wherever they're more specific — match the actual patterns they describe (sentence rhythm, what's named concretely vs left vague, how numbers are given, etc.).

CONTINUITY: the material below includes recent daily threads. Read them first. Don't repeat the same points or re-explain things already covered — build on the narrative instead (e.g. if something was 'in progress' before, say whether it's done now). If today doesn't clearly connect to recent days, that's fine, just don't restate old ground.

PROGRESS vs PROCESS MUST BE MECE — mutually exclusive, no overlapping information:
- Progress = the WHAT. The goal and what got achieved/built today, as an outcome. Never mention tools, methods, or how it was done here.
- Process = the HOW. The tools used, methods, and tactical approach taken to get there — concrete and specific about what was used (e.g. 'set up a Telegram bot for review', 'wrote a cron job for daily posting', 'drafted a few-shot prompt with example tweets to model the tone after'), but keep it conceptual, not code-level (no file names, function names, line-level implementation detail). Never restate what was achieved here — that's Progress's job.
Before finalizing, check: does any sentence in Progress describe a tool/method? Move it to Process. Does any sentence in Process describe an outcome/result? Move it to Progress.

DAY COUNTER: $DAY_NUMBER is a running count of this whole daily-writing practice, not a per-project counter — it does NOT reset when the project changes from yesterday, even if today is genuinely the first day working on something new. Output the literal line \"Day $DAY_NUMBER\" exactly as given below, verbatim, regardless of what project today is about.

Output EXACTLY 3 tweets using this delimiter format, nothing else:

===TWEET1===
Day $DAY_NUMBER

Project: <short project name, a few words>

Progress: <the WHAT only — goal and outcome, casual reflective tone, no tools/methods>
===TWEET2===
Process: <the HOW only — tools/methods/approach used, someone else could follow this as a playbook, no outcomes restated>
===TWEET3===
Takeaways: <the actual insight or lesson from today, reflective, a few sentences is fine — can include a forward-looking note like what you'd change or do next>

Each full tweet (including its labels and blank lines) must be at most 280 characters. If multiple projects were touched, focus on whichever was most substantive. No preamble, no extra commentary outside the three delimited blocks."

if claude -p --no-session-persistence --disallowedTools Write Edit Bash NotebookEdit Agent WebFetch WebSearch -- "$PROMPT" < "$CONTEXT_FILE" | python3 "$DIR/format_daily_draft.py" "$DRAFT_FILE"; then
  if python3 "$DIR/thread_review.py" send "$DATE" 2>>"$DIR/run_daily.err.log"; then
    osascript -e "display notification \"Thread sent to Telegram for review.\" with title \"Daily Learning Tweet\""
  else
    osascript -e "display notification \"Draft ready in $DRAFT_FILE — Telegram not configured, run approve.sh instead.\" with title \"Daily Learning Tweet\""
  fi
else
  osascript -e "display notification \"Could not parse today's draft — check run_daily.err.log.\" with title \"Daily Learning Tweet\""
  exit 1
fi
