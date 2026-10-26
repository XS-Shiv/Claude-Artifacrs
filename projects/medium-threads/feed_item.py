"""Turn a Medium RSS item into clean essay text for the thread prompt.

This is the "Clean Essay" step of the Medium -> X Threads automation. Medium's
feed carries each essay as HTML in <content:encoded>, ends it with an
"originally published in ..." footer and adds a tracking query to the link.
This step strips the HTML into plain paragraphs, decodes entities, drops the
footer and the tracking query, and returns title, link, guid and text.

Usage:
    python feed_item.py feed.xml            # first item in the feed
    python feed_item.py feed.xml --index 2 --json
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
BLOCKS = {"p", "h1", "h2", "h3", "h4", "li", "blockquote", "pre", "br"}
SKIP = {"script", "style", "figure"}  # images and their captions
FOOTER = re.compile(r"^.{0,200}\bwas originally published in\b.*$", re.I | re.S)


class _Text(HTMLParser):
    """Collect visible text, one paragraph per block element."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        if tag in BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP and self.skip:
            self.skip -= 1
        if tag in BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    """Plain text with one blank line between paragraphs and no footer."""
    parser = _Text()
    parser.feed(markup)
    parser.close()
    text = "".join(parser.parts).replace("\xa0", " ")
    paras = [re.sub(r"[ \t\r\f\v]+", " ", p).strip() for p in text.split("\n")]
    paras = [p for p in paras if p]
    if paras and FOOTER.match(paras[-1]):
        paras.pop()
    return "\n\n".join(paras)


def clean_link(link: str) -> str:
    """Drop the query and fragment Medium adds for tracking (?source=rss...)."""
    parts = urlsplit(link.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_item(item: ET.Element) -> dict:
    """Title, clean link, guid and essay text from one <item>."""
    title = html.unescape((item.findtext("title") or "").strip())
    link = clean_link(item.findtext("link") or "")
    guid = (item.findtext("guid") or link).strip()
    body = item.findtext(CONTENT) or item.findtext("description") or ""
    if not title or not link:
        raise ValueError("item has no title or link")
    return {"guid": guid, "title": title, "link": link, "text": html_to_text(body)}


def read_feed(xml: str) -> list[dict]:
    """Every item in an RSS feed, in feed order."""
    root = ET.fromstring(xml)
    return [parse_item(item) for item in root.iter("item")]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("feed", type=Path, help="RSS feed saved as XML")
    ap.add_argument("--index", type=int, default=0, help="which item, 0 is the first")
    ap.add_argument("--json", action="store_true", help="print the item as JSON")
    args = ap.parse_args(argv)
    try:
        items = read_feed(args.feed.read_text(encoding="utf-8"))
        item = items[args.index]
    except (OSError, ET.ParseError, ValueError, IndexError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(item, ensure_ascii=False, indent=2))
    else:
        print(f"{item['title']}\n{item['link']}\n\n{item['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
