#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATE="${1:-$(date +%Y-%m-%d)}"
DRAFT_FILE="$HOME/learning-log/drafts/$DATE.txt"
SUBSTACK_NOTE_FILE="$HOME/learning-log/drafts/$DATE-substack-note.txt"

if [ ! -f "$DRAFT_FILE" ]; then
  echo "No draft found at $DRAFT_FILE"
  exit 1
fi

STATE_FILE="$DIR/state/thread_state.json"
if [ -f "$STATE_FILE" ]; then
  STATUS=$(python3 -c "
import json
state = json.load(open('$STATE_FILE'))
print(state.get('status', '') if state.get('date') == '$DATE' else '')
" 2>/dev/null || echo "")
  if [ "$STATUS" = "done" ]; then
    echo "This thread was already approved and posted via Telegram. Nothing to do."
    exit 0
  fi
fi

echo "--- Twitter thread for $DATE (3 tweets) ---"
cat "$DRAFT_FILE"
echo "---"
echo
echo "Edit $DRAFT_FILE now if you want changes (keep the ===TWEETn=== delimiter format), then come back here."
read -r -p "Post this thread? [y/N] " confirm

if [[ "$confirm" =~ ^[Yy]$ ]]; then
  python3 "$DIR/post_tweet.py" "$DRAFT_FILE"
  python3 -c "
import json
from pathlib import Path
state_file = Path('$STATE_FILE')
state_file.parent.mkdir(parents=True, exist_ok=True)
state_file.write_text(json.dumps({'date': '$DATE', 'status': 'done', 'draft_path': '$DRAFT_FILE'}, indent=2))
"
else
  echo "Not posted."
fi

if [ -f "$SUBSTACK_NOTE_FILE" ]; then
  echo
  echo "--- Substack Note draft (post manually — no public API for Notes) ---"
  cat "$SUBSTACK_NOTE_FILE"
  echo "---"
fi
