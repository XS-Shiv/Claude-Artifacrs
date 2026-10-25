"""Turn drafted tweets into a thread that is safe to post to X.

This is the "Build Thread" step of the Medium -> X Threads automation. A model
drafts the tweets from an essay; this step cleans them up before anything is
posted: links are stripped (the essay link goes in its own last tweet), empty
tweets are dropped, at most six are kept, each is cut to 280 characters at a
word boundary, and a final tweet links to the full essay.

Usage:
    python thread.py draft.json
    python thread.py draft.json --json

draft.json holds {"title": ..., "link": ..., "tweets": ["...", ...]}.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence

MAX_CHARS = 280      # X's limit for one tweet
MAX_TWEETS = 6       # drafted tweets kept, before the link tweet
MIN_TWEETS = 3       # fewer usable tweets than this and nothing is posted
TITLE_CHARS = 200    # the title is cut to this in the link tweet
URL = re.compile(r"https?://\S+")


class ThreadError(ValueError):
    """The draft cannot be turned into a thread worth posting."""


def cap(text: str, limit: int = MAX_CHARS) -> str:
    """Cut text to at most `limit` characters, ending in an ellipsis.

    The cut goes back to the last space when that keeps at least 70% of the
    limit, so a word is not split in half; otherwise it cuts mid-word.
    """
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    space = cut.rfind(" ")
    if space > limit * 0.7:
        cut = cut[:space]
    return cut + "…"


def clean(tweet: object) -> str:
    """Remove links and outer spaces from one drafted tweet."""
    text = "" if tweet is None else str(tweet)
    return URL.sub("", text).strip()


def link_tweet(title: str, link: str) -> str:
    return f"Full essay: {cap(title, TITLE_CHARS)}\n{link}"


def build_thread(tweets: Iterable[object], title: str, link: str) -> list[str]:
    """The tweets to post, in order, ending with the link to the essay."""
    kept = [cap(t) for t in (clean(t) for t in tweets) if t][:MAX_TWEETS]
    if len(kept) < MIN_TWEETS:
        raise ThreadError(
            f"only {len(kept)} usable tweets in the draft; need at least {MIN_TWEETS}, "
            "so nothing would be posted"
        )
    return kept + [link_tweet(title, link)]


def format_thread(thread: Sequence[str]) -> str:
    """A preview of the thread with each tweet's position and length."""
    blocks = []
    for n, tweet in enumerate(thread, 1):
        blocks.append(f"[{n}/{len(thread)}] {len(tweet)} chars\n{tweet}")
    return "\n\n".join(blocks)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a postable X thread from drafted tweets.")
    parser.add_argument("draft", help='JSON file with "title", "link" and "tweets"')
    parser.add_argument("--json", action="store_true", help="print the thread as a JSON list")
    args = parser.parse_args(argv)
    path = Path(args.draft)
    if not path.is_file():
        parser.error(f"no such file: {args.draft}")
    try:
        draft = json.loads(path.read_text(encoding="utf-8"))
        thread = build_thread(draft.get("tweets") or [], draft["title"], draft["link"])
    except (json.JSONDecodeError, KeyError, AttributeError) as err:
        print(f"thread.py: {path.name} is not a draft: {err}", file=sys.stderr)
        return 2
    except ThreadError as err:
        print(f"thread.py: {err}", file=sys.stderr)
        return 1
    print(json.dumps(thread, ensure_ascii=False, indent=2) if args.json else format_thread(thread))
    return 0


if __name__ == "__main__":
    sys.exit(main())
