"""Keep the posted log: one JSON record per essay already threaded on X.

This is the "Remember Posted" step of the Medium -> X Threads automation. After
a thread goes up, the essay's guid, title, link and the root tweet id are added
to a local JSON file, so `next_essay.py --posted` skips it on the next run.

The file is a JSON list of objects. Older logs that hold bare guid strings are
read too and written back as objects. A guid is recorded once; adding it again
is refused so a re-run cannot post the same essay twice. Writes go to a temp
file first and replace the log in one step, so a crash never leaves half a file.

Usage:
    python posted_log.py add posted.json --guid G --title T --link L --tweet-id 123
    python posted_log.py list posted.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ("guid", "title", "link", "tweet_id")


def normalise(entry) -> dict:
    """One log entry as a record; a bare string is taken as the guid."""
    record = {"guid": entry} if isinstance(entry, str) else entry
    if not isinstance(record, dict):
        raise ValueError(f"posted entry is not an object: {entry!r}")
    guid = record.get("guid")
    if not isinstance(guid, str) or not guid.strip():
        raise ValueError(f"posted entry has no guid: {entry!r}")
    return {**record, "guid": guid.strip()}


def load(path: Path) -> list[dict]:
    """Records in the log, oldest first; a missing file is an empty log."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8") or "[]")
    if not isinstance(data, list):
        raise ValueError("posted log must be a JSON list")
    return [normalise(e) for e in data]


def save(path: Path, records: list[dict]) -> None:
    """Write the log atomically: temp file in the same folder, then replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def record(guid: str, title: str, link: str, tweet_id: str, now: datetime | None = None) -> dict:
    """A new log record; the tweet id must be digits, as X ids are."""
    values = {"guid": guid, "title": title, "link": link, "tweet_id": str(tweet_id)}
    values = {k: v.strip() for k, v in values.items()}
    missing = [k for k in FIELDS if not values[k]]
    if missing:
        raise ValueError(f"missing {', '.join(missing)}")
    if not values["tweet_id"].isdigit():
        raise ValueError(f"tweet id must be digits: {tweet_id!r}")
    when = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {**values, "posted_at": when.replace(microsecond=0).isoformat()}


def add(path: Path, new: dict) -> list[dict]:
    """Append a record unless its guid is already logged; returns the log."""
    records = load(path)
    if any(r["guid"] == new["guid"] for r in records):
        raise ValueError(f"already posted: {new['guid']}")
    records.append(new)
    save(path, records)
    return records


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="record a posted thread")
    a.add_argument("log", type=Path)
    a.add_argument("--guid", required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--link", required=True)
    a.add_argument("--tweet-id", required=True, help="id of the thread's first tweet")
    ls = sub.add_parser("list", help="print the log, newest first")
    ls.add_argument("log", type=Path)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "add":
            new = record(args.guid, args.title, args.link, args.tweet_id)
            records = add(args.log, new)
            print(f"logged {new['guid']} ({len(records)} posted)")
        else:
            for r in reversed(load(args.log)):
                print(f"{r.get('posted_at', '-')[:10]}  {r.get('tweet_id', '-'):>20}  {r.get('title', r['guid'])}")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if str(exc).startswith("already posted") else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
