#!/usr/bin/env python3
"""Mechanical checks for a dailypush-x thread.json.

Usage: check_thread.py path/to/thread.json
Prints PASS/FAIL per check and exits 1 if any check fails, 2 on a bad file.
"""
import json
import re
import sys

URL = re.compile(r"https?://\S+")
HASHTAG = re.compile(r"(^|\s)#\w")
NUMBERING = re.compile(r"^\s*\(?\d+\s*/\s*\d*\)?|\(?\b\d+\s*/\s*\d+\)?\s*$")
EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]"
)
LIMIT = 280
URL_WEIGHT = 23


def char_weight(ch):
    # twitter-text v3: these ranges count 1, everything else (CJK, emoji) counts 2
    cp = ord(ch)
    light = (
        (0x0000, 0x10FF), (0x2000, 0x200D), (0x2010, 0x201F), (0x2032, 0x2037),
    )
    return 1 if any(lo <= cp <= hi for lo, hi in light) else 2


def x_length(text):
    stripped = URL.sub("", text)
    return sum(char_weight(c) for c in stripped) + URL_WEIGHT * len(URL.findall(text))


def main(path):
    try:
        with open(path, encoding="utf-8") as f:
            draft = json.load(f)
        tweets = draft["tweets"]
        assert isinstance(tweets, list) and all(isinstance(t, str) for t in tweets)
    except (OSError, ValueError, KeyError, AssertionError) as e:
        print(f"not a thread.json: {e}")
        return 2

    results = []

    def check(name, failures):
        results.append((name, failures))

    check("3 to 5 tweets", [] if 3 <= len(tweets) <= 5 else [f"{len(tweets)} tweets"])

    over = []
    for i, t in enumerate(tweets, 1):
        n = x_length(t)
        print(f"  tweet {i}: {n} chars")
        if n > LIMIT:
            over.append(f"tweet {i} is {n}")
    check("every tweet <= 280 (X counting)", over)

    link_fails = []
    for i, t in enumerate(tweets[:-1], 1):
        if URL.search(t):
            link_fails.append(f"link in tweet {i}")
    if tweets and len(URL.findall(tweets[-1])) != 1:
        link_fails.append("last tweet must have exactly one link")
    check("one link, last tweet only", link_fails)

    banned = []
    for i, t in enumerate(tweets, 1):
        if HASHTAG.search(t):
            banned.append(f"hashtag in tweet {i}")
        if EMOJI.search(t):
            banned.append(f"emoji in tweet {i}")
        if NUMBERING.search(URL.sub("", t)):
            banned.append(f"numbering in tweet {i}")
        if "—" in t:
            banned.append(f"em dash in tweet {i}")
    check("no hashtags, emojis, numbering or em dashes", banned)

    seen, dupes = set(), []
    for i, t in enumerate(tweets, 1):
        key = " ".join(t.split()).lower()
        if not key:
            dupes.append(f"tweet {i} is empty")
        elif key in seen:
            dupes.append(f"tweet {i} repeats an earlier tweet")
        seen.add(key)
    check("no empty or duplicate tweets", dupes)

    failed = False
    for name, failures in results:
        if failures:
            failed = True
            print(f"FAIL — {name}: {'; '.join(failures)}")
        else:
            print(f"PASS — {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip())
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
