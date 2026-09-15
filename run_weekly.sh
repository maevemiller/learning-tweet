#!/bin/bash
set -euo pipefail

export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATE="$(date +%Y-%m-%d)"
WEEK_LABEL="$(date +%Y-W%V)"

WEEKLY_DIR="$HOME/learning-log/weekly"
mkdir -p "$WEEKLY_DIR"

DIGEST_FILE="$(mktemp)"
trap 'rm -f "$DIGEST_FILE"' EXIT

python3 "$DIR/weekly_digest.py" "$DATE" > "$DIGEST_FILE"

CONTENT_CHARS=$(grep -v '^===' "$DIGEST_FILE" | grep -v '^##' | tr -d '[:space:]' | wc -c | tr -d ' ')

if [ "$CONTENT_CHARS" -lt 20 ]; then
  osascript -e "display notification \"No activity found this week — skipping weekly write-up.\" with title \"Weekly Write-Up\""
  exit 0
fi

LINKEDIN_FILE="$WEEKLY_DIR/$WEEK_LABEL-linkedin.txt"
SUBSTACK_FILE="$WEEKLY_DIR/$WEEK_LABEL-substack.md"

STYLE_CLAUSE="Sound like a real person, not an AI: no em dashes (use periods or commas instead), no filler like 'it's worth noting' or 'game-changer' or 'at the end of the day', no throat-clearing intros. Write as things I decided and did as the builder, not as narration of what an AI assistant did on my behalf."

LINKEDIN_PROMPT="You are drafting a LinkedIn post recapping my past week of side-project progress, based ONLY on the session content and daily tweet recap piped to you below. Write in first-person, reflective but professional tone. 3-6 short paragraphs or a few punchy lines with line breaks — whatever fits the material, LinkedIn readers skim. Focus on genuine technical progress and what I learned, not routine chores. At most 2-3 relevant hashtags at the very end, or none. Do not invent details not present in the input. $STYLE_CLAUSE Output ONLY the post text, no preamble or explanation."

SUBSTACK_PROMPT="You are drafting a longer-form Substack post (markdown) recapping my past week of side-project progress, based ONLY on the session content and daily tweet recap piped to you below. Use a title (# heading), then a few sections with short headers if useful. Narrative, first-person, more detail and reflection than a LinkedIn post — this is for people who want the fuller story of what I built/learned this week and why it mattered. Do not invent details not present in the input. $STYLE_CLAUSE Output ONLY the markdown post, no preamble or explanation."

claude -p --no-session-persistence --disallowedTools Write Edit Bash NotebookEdit Agent WebFetch WebSearch -- "$LINKEDIN_PROMPT" < "$DIGEST_FILE" > "$LINKEDIN_FILE"
claude -p --no-session-persistence --disallowedTools Write Edit Bash NotebookEdit Agent WebFetch WebSearch -- "$SUBSTACK_PROMPT" < "$DIGEST_FILE" > "$SUBSTACK_FILE"

osascript -e "display notification \"Weekly drafts ready: $LINKEDIN_FILE and $SUBSTACK_FILE\" with title \"Weekly Write-Up\""
