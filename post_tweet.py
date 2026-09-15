#!/usr/bin/env python3
"""Post a 3-tweet daily draft as a Twitter thread, using credentials stored in
macOS Keychain.

Credentials must be pre-populated once via `security add-generic-password`
(see SETUP.md in this directory) under service name "learning-tweet-twitter",
with accounts: api_key, api_secret, access_token, access_token_secret.

Expects the draft file to contain delimited blocks (===TWEET1===, ===TWEET2===,
etc. — normally 3, as written by format_daily_draft.py, but any count works).
Tweet 1 is posted as the root tweet; the rest are chained as replies in
order, so the thread reads top to bottom.
"""
import re
import subprocess
import sys
from pathlib import Path

SERVICE = "learning-tweet-twitter"
ACCOUNTS = ["api_key", "api_secret", "access_token", "access_token_secret"]
DELIMITER_RE = re.compile(r"^===TWEET(\d)===\s*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_secret(account):
    result = subprocess.run(
        ["security", "find-generic-password", "-s", SERVICE, "-a", account, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"Missing Keychain entry for account '{account}' under service '{SERVICE}'. "
            f"See SETUP.md.",
            file=sys.stderr,
        )
        sys.exit(1)
    return result.stdout.strip()


def parse_draft(text):
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

    if not tweets:
        print("No ===TWEETn=== blocks found in draft.", file=sys.stderr)
        sys.exit(1)

    numbers = sorted(tweets)
    if numbers != list(range(1, len(numbers) + 1)):
        print(f"Tweet numbers must be consecutive starting at 1, got: {numbers}", file=sys.stderr)
        sys.exit(1)

    empty = [n for n in numbers if not tweets[n]]
    if empty:
        print(f"Tweet(s) are empty: {empty}", file=sys.stderr)
        sys.exit(1)

    for n in numbers:
        if len(tweets[n]) > 280:
            print(f"Tweet {n} is {len(tweets[n])} chars, over the 280 limit. Aborting.", file=sys.stderr)
            sys.exit(1)

    return [tweets[n] for n in numbers]


def main():
    if len(sys.argv) != 2:
        print("usage: post_tweet.py <path-to-draft-file>", file=sys.stderr)
        sys.exit(1)

    draft_path = sys.argv[1]
    with open(draft_path) as f:
        text = f.read().strip()

    if not text:
        print("Draft file is empty, nothing to post.", file=sys.stderr)
        sys.exit(1)

    tweets = parse_draft(text)

    try:
        import tweepy
    except ImportError:
        print("tweepy is not installed. Run: pip3 install tweepy", file=sys.stderr)
        sys.exit(1)

    creds = {account: get_secret(account) for account in ACCOUNTS}

    client = tweepy.Client(
        consumer_key=creds["api_key"],
        consumer_secret=creds["api_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )

    previous_id = None
    posted_ids = []
    for tweet_text in tweets:
        response = client.create_tweet(
            text=tweet_text,
            in_reply_to_tweet_id=previous_id,
        )
        previous_id = response.data["id"]
        posted_ids.append(previous_id)

    print(f"Posted thread: {posted_ids}")

    # Close the loop: capture what just got posted into the golden set / voice
    # lessons, so future generation learns from it. Only for dated draft files
    # (skips ad-hoc test posts) — doesn't fail the post if extraction errors.
    date_stem = Path(draft_path).stem
    if DATE_RE.match(date_stem):
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            import capture_golden_example

            capture_golden_example.capture(date_stem, text)
        except Exception as e:
            print(f"(posted fine, but golden-set capture failed: {e})", file=sys.stderr)


if __name__ == "__main__":
    main()
