"""Posting order from the tier list: S and A essays only, topics alternating.

Not every essay is worth a thread. The tier list ranks each one S, A, B or C
and tags it with a topic, "design-ai" or "web3". Only S and A essays are
queued. Within a topic, S comes before A and ties keep the list's order. The
queue then alternates topics, starting with the one the last posted essay was
not, so two Web3 threads never land back to back; when one topic runs out the
rest of the other follows.

The tier list is a JSON list of {"guid", "title", "tier", "topic"} objects.
The posted log is the file `posted_log.py` writes (oldest first).

Usage:
    python tier_order.py tiers.json --posted posted.json
    python tier_order.py tiers.json --posted posted.json --next --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import posted_log

TIERS = ("S", "A", "B", "C")
QUEUED = ("S", "A")
TOPICS = ("design-ai", "web3")
ALIASES = {"design": "design-ai", "ai": "design-ai", "design/ai": "design-ai", "web 3": "web3"}


def parse_tiers(data) -> list[dict]:
    """Validated tier entries with tier upper-cased and topic normalised."""
    if not isinstance(data, list):
        raise ValueError("tier list must be a JSON list")
    seen, out = set(), []
    for entry in data:
        if not isinstance(entry, dict) or not str(entry.get("guid", "")).strip():
            raise ValueError(f"tier entry has no guid: {entry!r}")
        guid = entry["guid"].strip()
        tier = str(entry.get("tier", "")).strip().upper()
        topic = str(entry.get("topic", "")).strip().lower()
        topic = ALIASES.get(topic, topic)
        if tier not in TIERS:
            raise ValueError(f"{guid}: tier must be one of {', '.join(TIERS)}, got {entry.get('tier')!r}")
        if topic not in TOPICS:
            raise ValueError(f"{guid}: topic must be one of {', '.join(TOPICS)}, got {entry.get('topic')!r}")
        if guid in seen:
            raise ValueError(f"{guid}: listed twice")
        seen.add(guid)
        out.append({**entry, "guid": guid, "tier": tier, "topic": topic})
    return out


def last_topic(tiers: list[dict], posted: list[dict]) -> str | None:
    """Topic of the most recently posted essay that is on the tier list."""
    topic_of = {t["guid"]: t["topic"] for t in tiers}
    for record in reversed(posted):
        if record["guid"] in topic_of:
            return topic_of[record["guid"]]
    return None


def posting_order(tiers: list[dict], posted: list[dict]) -> list[dict]:
    """S and A essays not yet posted, alternating topics."""
    done = {r["guid"] for r in posted}
    queues = {
        topic: sorted(
            (t for t in tiers if t["topic"] == topic and t["tier"] in QUEUED and t["guid"] not in done),
            key=lambda t: QUEUED.index(t["tier"]),  # stable: ties keep list order
        )
        for topic in TOPICS
    }
    previous = last_topic(tiers, posted)
    if previous is None:
        # Nothing posted yet: lead with the topic of the best, earliest essay.
        heads = [q[0] for q in queues.values() if q]
        if not heads:
            return []
        best = min(heads, key=lambda t: (QUEUED.index(t["tier"]), tiers.index(t)))
        turn = best["topic"]
    else:
        turn = TOPICS[1 - TOPICS.index(previous)]
    order = []
    while queues["design-ai"] or queues["web3"]:
        if not queues[turn]:
            turn = TOPICS[1 - TOPICS.index(turn)]
        order.append(queues[turn].pop(0))
        turn = TOPICS[1 - TOPICS.index(turn)]
    return order


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tiers", type=Path, help="tier list as JSON")
    ap.add_argument("--posted", type=Path, help="posted log written by posted_log.py")
    ap.add_argument("--next", action="store_true", help="print only the next essay")
    ap.add_argument("--json", action="store_true", help="print JSON")
    args = ap.parse_args(argv)
    try:
        tiers = parse_tiers(json.loads(args.tiers.read_text(encoding="utf-8")))
        posted = posted_log.load(args.posted) if args.posted else []
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    order = posting_order(tiers, posted)
    if not order:
        print("nothing queued: every S and A essay is posted", file=sys.stderr)
        return 1
    if args.next:
        order = order[:1]
    if args.json:
        print(json.dumps(order[0] if args.next else order, ensure_ascii=False, indent=2))
    else:
        for n, t in enumerate(order, 1):
            print(f"{n:>2}. {t['tier']}  {t['topic']:<9}  {t.get('title') or t['guid']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
