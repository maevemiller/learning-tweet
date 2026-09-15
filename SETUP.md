# Daily Learning Tweet — Setup

One-time setup steps. Everything after this runs on its own.

## 1. Twitter/X API access

1. Go to developer.twitter.com and create a Developer App (any tier that allows posting — the free tier supports a limited number of tweets/month, which is plenty for one tweet a day).
2. In the app's settings, set permissions to **Read and Write**.
3. Generate/regenerate these four values (regenerating after changing permissions is required, or old keys won't have write access):
   - API Key
   - API Key Secret
   - Access Token
   - Access Token Secret

## 2. Install tweepy

```
pip3 install tweepy
```

## 3. Store credentials in macOS Keychain

Run these once (replace the placeholder values), then close the terminal — nothing else needs to see the raw values again:

```
security add-generic-password -s learning-tweet-twitter -a api_key -w 'YOUR_API_KEY' -U
security add-generic-password -s learning-tweet-twitter -a api_secret -w 'YOUR_API_SECRET' -U
security add-generic-password -s learning-tweet-twitter -a access_token -w 'YOUR_ACCESS_TOKEN' -U
security add-generic-password -s learning-tweet-twitter -a access_token_secret -w 'YOUR_ACCESS_TOKEN_SECRET' -U
```

Verify they're readable:

```
security find-generic-password -s learning-tweet-twitter -a api_key -w
```

## 4. Test posting once, by hand

```
printf '===TWEET1===\nDay 0\n\nProject: learning-tweet\n\nProgress: Testing my daily thread pipeline.\n===TWEET2===\nProcess: Tested by hand before trusting the schedule.\n===TWEET3===\nTakeaways: Always test the real posting path once.\n' > /tmp/test-thread.txt
python3 ~/dev/learning-tweet/post_tweet.py /tmp/test-thread.txt
```

Confirm the 3-tweet thread shows up on your timeline (as a proper reply chain, not 3 separate top-level tweets) before trusting the automated flow.

## 5. Load the daily schedule

```
launchctl load ~/Library/LaunchAgents/com.minmiller.learningtweet.plist
launchctl list | grep learningtweet
```

This runs `run_daily.sh` every day at 8:00pm. It:
- Scans today's Claude Code transcripts, Cursor chats, and Hermes sessions automatically.
- Reads `~/learning-log/notes/YYYY-MM-DD.md` for anything you jotted in yourself.
- If there's nothing to report, it just notifies you and stops — no forced thread.
- Otherwise drafts a 3-tweet Twitter thread to `~/learning-log/drafts/YYYY-MM-DD.txt` (delimited `===TWEET1===`/`===TWEET2===`/`===TWEET3===` blocks): tweet 1 is "Day N / Project: .../Progress: ...", tweet 2 is "Process: ...", tweet 3 is "Takeaways: ...". "Day N" is a running counter (see below) — tweet 1 is the standalone lead, tweets 2-3 reply in order underneath it. Also writes a Substack Note draft at `~/learning-log/drafts/YYYY-MM-DD-substack-note.txt` (tweet 1's text, meant to be pasted into Substack Notes by hand — Notes has no public posting API).
- Sends the whole thread to your Telegram bot for review (see below) — this is the main way you sign off before anything posts.

### The "Day N" counter

`day_number.py` tracks this via `state/day_zero.txt` (just a date). Day N = elapsed calendar days since that date, +1 — so a day with nothing to report just shows up as a gap (Day 5, then Day 7) rather than needing separate tracking. It was created automatically on first run of the new format; edit `state/day_zero.txt` directly (a single `YYYY-MM-DD` date) if you want to backdate it to when you actually started.

## 6. Review and post each day — via Telegram

Each evening's thread gets sent to your Telegram bot automatically (shared with the `ai-content` news pipeline's bot/poller). Reply **"approved"** to post it, or send any feedback (e.g. "make the takeaways punchier") to get a revised version — it'll keep looping until you approve. Nothing posts without that reply.

`~/dev/learning-tweet/approve.sh` still works as a terminal fallback (shows the draft, asks y/N, posts on confirm) if you'd rather not use Telegram for a given day — it checks state first and won't double-post if you already approved via Telegram.

## Day to day

- Jot quick notes anytime into `~/learning-log/notes/$(date +%Y-%m-%d).md` — they'll get folded into that evening's draft.
- To run the collection step manually instead of waiting for 8pm: `bash ~/dev/learning-tweet/run_daily.sh`
- To change the run time, edit the `Hour`/`Minute` values in `~/Library/LaunchAgents/com.minmiller.learningtweet.plist`, then:
  ```
  launchctl unload ~/Library/LaunchAgents/com.minmiller.learningtweet.plist
  launchctl load ~/Library/LaunchAgents/com.minmiller.learningtweet.plist
  ```
- To stop the automation entirely: `launchctl unload ~/Library/LaunchAgents/com.minmiller.learningtweet.plist`

## Weekly LinkedIn + Substack write-up

`com.minmiller.learningtweet.weekly.plist` runs `run_weekly.sh` every Sunday at 6:00pm. It aggregates the past 7 days (Claude Code/Cursor/Hermes sessions + that week's daily tweet drafts) into two drafts:

- `~/learning-log/weekly/YYYY-Www-linkedin.txt` — copy/paste into LinkedIn yourself.
- `~/learning-log/weekly/YYYY-Www-substack.md` — post manually, or via your Substack's "post by email" address (Settings → your publication → look for the posting email address).

Neither platform has a workable posting API for a personal account (LinkedIn needs app review; Substack has none at all), so this stays draft-only by design — no Keychain credentials needed for this part.

To run it manually: `bash ~/dev/learning-tweet/run_weekly.sh`

## Manual-writing mode + the self-improving voice loop

As of 2026-09-09, daily auto-generation is **paused** (`launchctl unload ~/Library/LaunchAgents/com.minmiller.learningtweet.plist`) while threads are being written by hand for a week or so, to build a reference set of real voice/tone examples. To resume automation: `launchctl load ~/Library/LaunchAgents/com.minmiller.learningtweet.plist`.

**The loop is closed as of 2026-09-10** — it's automatic now, not a manual step:
1. Write the thread directly into `~/learning-log/drafts/YYYY-MM-DD.txt` in the `===TWEET1===`/`===TWEET2===`/... format (any number of tweets — `post_tweet.py` no longer requires exactly 3).
2. Post it (via `approve.sh`, Telegram approval, or ask me to post it directly).
3. `post_tweet.py` automatically captures it into `golden-set/` and extends `voice-lessons.md` (a running, accumulating style guide, via a `claude -p` call comparing the new example against the doc so far) right after a successful post. No separate step needed. (Manual invocation — `python3 capture_golden_example.py YYYY-MM-DD` — still works if you ever need to backfill or re-run one.)
4. `run_daily.sh` and `thread_review.py`'s revision prompt both read `voice-lessons.md` and feed it into the next generation/revision, explicitly told to prioritize it over the generic style guidance already in the prompt. Confirmed working 2026-09-10 — a lesson extracted from the Day 2 example ("finally" as a personality/friction word) showed up verbatim in the next auto-generated draft.

**Known limitation, worth watching once back in automated mode:** capture currently happens on *every* successful post, with no distinction between a hand-written thread, a heavily-revised one, and one approved with zero edits. During manual-writing mode this is fine — everything posted is by definition hand-written. But once automation resumes, a thread approved without any edits is a weaker signal of "this is the target voice" than one you revised — feeding it back in unchanged risks the loop reinforcing the model's own generic tendencies rather than your actual voice. If that starts showing up (lessons drifting generic, or repeating themselves), the fix is to gate capture on `revision_count > 0` (real edits happened) instead of every post — not implemented yet since it's not yet a problem.

## Expanding to more channels later

The draft format is deliberately channel-agnostic: `run_daily.sh` produces one structured draft (3 delimited tweets) and a plain-text extract of tweet 1, then hands them off to channel-specific posters — currently just `post_tweet.py`. Adding a channel later means writing one more small poster script that reads the same draft file:
- **Substack Notes**: already drafted as `-substack-note.txt`; automating the post itself would need Substack to expose a public API for Notes, which doesn't currently exist — worth rechecking if that changes.
- **TikTok**: fundamentally different — it needs an actual video, not text, so this would plug in at the same place the `ai-content` video-script pipeline does (a script to read on camera), not as a text poster. Posting via API also needs Content Posting API approval for a personal account.

## Known limitations

- Cursor has no per-message timestamp, only a per-chat-tab "last sent" time, so a chat tab is included if it was last touched today (an edge case around midnight could pull in a little of yesterday too).
- Hermes's session database (`~/.hermes/state.db`) was empty at setup time (no chats recorded yet there), so `collect_hermes.py` is untested against real Hermes conversation content — the schema is solid (`messages`/`sessions` tables with proper timestamps), so it should work once you actually use Hermes, but worth checking the first time it has real data.
- Fixed 2026-09-06: `collect_claude_code.py` originally compared UTC timestamps against local dates via naive string matching, which could attribute evening work to the wrong calendar day. Now converts to local time before comparing.
- Fixed 2026-09-06: headless `claude -p` synthesis calls were writing their own transcripts back into `~/.claude/projects`, which the next day's collector would then treat as real activity. All `claude -p` calls across this system now use `--no-session-persistence`.
- Changed 2026-09-06: daily output became a 5-tweet thread (TLDR/PROJECT/PROGRESS/PROCESS/LEARNINGS) instead of a single tweet.
- Changed 2026-09-08: reworked to a 3-tweet thread (Day N/Project/Progress, then Process, then Takeaways) with a running day counter, and sign-off moved to Telegram (reply "approved" or send feedback to revise) instead of only the terminal `approve.sh` flow. Each tweet has a hard 280-char safety-net truncation (mid-sentence, ending in "...") in case the model runs long on a dense day — check the draft before approving on days with a lot going on.
- Changed 2026-09-08: Process is now explicitly high-level (decisions/tools/workflow, never file names or code detail) and framed as things "I" did as the builder, not narration of what the AI assistant did — written for an audience trying to build something similar themselves. Same voice/audience framing applied to the weekly LinkedIn/Substack drafts and the ai-content video scripts.
- Added 2026-09-08: `recent_threads.py` feeds the last 5 days' threads into today's prompt as context, so the model doesn't repeat itself and can reference what was previously in progress. The "any activity today?" check happens before this context is added, so a quiet day still correctly produces no tweet.
- Added 2026-09-08: style guardrails against AI-sounding text (no em dashes, no filler like "it's worth noting" or "game-changer", no throat-clearing intros) across the daily thread, weekly write-up, and video scripts.
- Changed 2026-09-08: dropped heavy first-person phrasing in favor of a telegraphic, build-in-public log style — "Set up a Telegram bot" instead of "I set up a Telegram bot", matching the tone of the original example format.
- Changed 2026-09-09: `post_tweet.py` now posts however many `===TWEETn===` blocks a draft has (was hardcoded to exactly 3) — needed for a day that pivoted projects mid-stream and wanted an extra "Context" tweet ahead of the usual Day/Project/Progress. Standard daily generation still targets exactly 3; the extra-tweet case is for manual edits.
- Added 2026-09-08: voice message feedback via Telegram, transcribed locally with mlx-whisper (no API key/cost). Found and fixed a routing bug this exposed — see ai-content/SETUP.md's state machine section.
- Fixed 2026-09-09: every `claude -p` call across this whole system (daily thread, weekly write-up, news/concept scripts, lesson extraction) had unrestricted tool access — normally harmless since nothing asked it to use one, but one prompt did trigger an actual Write tool attempt, which got silently denied and then narrated in the output text instead of erroring cleanly. `--allowedTools ""` looked like a fix but is actually a no-op — worse, `--allowedTools`/`--disallowedTools` are variadic and silently swallow the next argv item (i.e. the whole prompt) if not terminated with `--`. Correct fix, now applied everywhere: `--disallowedTools Write Edit Bash NotebookEdit Agent WebFetch WebSearch -- "$PROMPT"`.
- Added 2026-09-09: manual-writing mode + the golden set — see below. Daily auto-generation paused while threads are hand-written for reference.
- Changed 2026-09-08: Progress and Process are now explicitly MECE — Progress is the WHAT (goal/outcome only, no tools/methods), Process is the HOW (tools/methods only, no outcomes restated). The prompt checks each sentence against the other section before finalizing.
- Added 2026-09-10: targeted revisions. Feedback that clearly names one tweet ("for the takeaways, make these changes", "tighten process") now only regenerates that tweet — `thread_review.detect_target_tweet()` keyword-matches the feedback to a tweet number, and if exactly one matches, only that tweet gets sent to claude for revision; the others are spliced back in verbatim, byte-identical, not just "asked" to stay the same. Ambiguous, multi-section, or generic feedback ("make it punchier") still falls back to revising the whole thread. Verified: a takeaways-only edit left tweets 1 and 2 diff-identical.
- Fixed 2026-09-11: `MAX_CHARS_PER_PROJECT`/`_TAB`/`_SESSION` in all three collectors was 3000 chars — way too low for a genuinely dense day. A whole shipped feature (a Settings tab for reminder customization) got silently truncated out of the context before the model ever saw it, on a day with a lot of real habit-tracker work. Raised all three to 20000, and changed truncation to keep the **tail** instead of the head — late-session content (fixes, final state, what actually shipped) matters more than early exploration, and head-truncation was quietly losing exactly that.
- Note 2026-09-11: on an unusually dense day, the standard 3-tweet generation kept picking one narrative angle instead of covering everything — regenerating with fuller feedback helped but still didn't include a specific feature the user asked about by name. Ended up hand-drafting a 5-tweet thread for that day. Worth watching whether this needs a standing "dense day" mode (e.g. explicitly listing every distinct feature/fix as its own beat) rather than relying on the model to decide it should expand on its own.
- Fixed 2026-09-14: Day counter reset to "Day 1" on its own the day the tracked project pivoted (Habit Tracker → NYC Events Newsletter), even though `day_number.py` correctly computed 7 and the correct value was injected into the prompt. The model was treating "Day N" as a semantic per-project counter and overriding the given value when a new project felt like a fresh start. Fixed by making the instruction explicit: the day counter tracks the whole daily-writing practice, not the current project, and must be output verbatim regardless of what today's project is about.
- Fixed 2026-09-14: `collect_cursor.py` only ever read the per-workspace `workbench.panel.aichat.view.aichat.chatdata` key, which is empty for Cursor's newer Background Composer / cloud-agent sessions — those run remotely and don't populate it at all. A full day of real background-composer activity (a habit-tracker backlog review) was silently invisible to the daily thread as a result. Cursor does index that activity separately, in `globalStorage/conversation-search.db` (a `conversations` + `conversation_fts` table pair with a real per-conversation `updated_at` timestamp and full message bodies) — added `collect_background_composer()` to query that too and merge it in. Confirmed both sources are needed: the search-index DB currently has zero "local" (regular chat) entries on this machine, only "cloud-cache" ones, so the original per-workspace collection still matters for normal chats.
- Fixed 2026-09-14: asking for a 4th tweet in a revision (e.g. "add an Also: tweet") kept silently losing the Takeaways tweet instead of actually adding one, net 3 tweets either way. Two stacked bugs: (1) `thread_review.py`'s revision prompt hardcoded "Here is a 3-tweet draft... output EXACTLY 3 tweets" with a literal `===TWEET1/2/3===` template, which fought against any feedback asking for a different count — fixed by making it read the actual current tweet count and instructing the model to preserve everything unless the feedback explicitly asks to add/remove one. (2) Even after that fix, `format_daily_draft.py`'s output-writing step *itself* hardcoded `for n in (1, 2, 3)`, silently discarding any 4th+ tweet claude actually produced, regardless of what the prompt asked for — this was the real root cause, and the more dangerous one, since it would've silently thrown away correct model output. Fixed to write however many consecutive tweets are actually present. Verified end to end: a real 4-tweet addition (Progress/Process/Also/Takeaways) now round-trips correctly with all 4 tweets preserved.
