"""Pick the next essay to thread: newest in the feed that is not posted yet.

This is the "Pick Essay" step of the Medium -> X Threads automation. It reads
the feed, drops every item whose guid is already in the posted log, sorts the
rest newest first by <pubDate> and returns one, so each run posts one essay.

The posted log is a JSON list; each entry is a guid string or an object with a
"guid" key. A missing log file means nothing has been posted yet.

Usage:
    python next_essay.py feed.xml --posted posted.json
    python next_essay.py feed.xml --posted posted.json --json
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feed_item

OLDEST = datetime.min.replace(tzinfo=timezone.utc)


def published(item: ET.Element) -> datetime:
    """The item's <pubDate> as an aware datetime; undated items sort last."""
    raw = (item.findtext("pubDate") or "").strip()
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return OLDEST
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def posted_guids(entries: list) -> set[str]:
    """Guids from a posted log whose entries are strings or {"guid": ...}."""
    if not isinstance(entries, list):
        raise ValueError("posted log must be a JSON list")
    guids = set()
    for entry in entries:
        guid = entry.get("guid") if isinstance(entry, dict) else entry
        if not isinstance(guid, str) or not guid.strip():
            raise ValueError(f"posted entry has no guid: {entry!r}")
        guids.add(guid.strip())
    return guids


def unposted(xml: str, posted: set[str]) -> list[dict]:
    """Items not yet posted, newest first; ties keep feed order."""
    root = ET.fromstring(xml)
    dated = []
    for order, el in enumerate(root.iter("item")):
        item = feed_item.parse_item(el)
        if item["guid"] in posted:
            continue
        item["published"] = published(el)
        dated.append((-item["published"].timestamp(), order, item))
    dated.sort(key=lambda t: (t[0], t[1]))
    return [item for *_, item in dated]


def next_essay(xml: str, posted: set[str]) -> dict | None:
    """The one essay to post this run, or None when all are posted."""
    items = unposted(xml, posted)
    return items[0] if items else None


def load_posted(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    return posted_guids(json.loads(path.read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("feed", type=Path, help="RSS feed saved as XML")
    ap.add_argument("--posted", type=Path, help="JSON list of posted guids")
    ap.add_argument("--json", action="store_true", help="print the essay as JSON")
    args = ap.parse_args(argv)
    try:
        posted = load_posted(args.posted)
        item = next_essay(args.feed.read_text(encoding="utf-8"), posted)
    except (OSError, ET.ParseError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if item is None:
        print("nothing new: every essay in the feed is posted", file=sys.stderr)
        return 1
    date = "undated" if item["published"] == OLDEST else item["published"].date().isoformat()
    if args.json:
        print(json.dumps({**item, "published": date}, ensure_ascii=False, indent=2))
    else:
        print(f"{item['title']}\n{item['link']}\n{date}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
