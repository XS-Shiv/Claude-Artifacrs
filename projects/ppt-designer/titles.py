"""List slides whose title names a topic instead of stating a conclusion.

The skill asks for action titles: a full sentence with a verb, and a number where
one exists. "Chennai resists quick commerce but offers a first-mover advantage"
passes; "Chennai market analysis" is topic-only.

A title counts as topic-only when it has no number and none of its words is a
known verb. The verb check is a word list, not a parser, so it errs towards
passing a title; a title it flags is almost always a topic label.

Usage:
    python titles.py deck.pptx            print every title, marking topic-only ones
    python titles.py deck.pdf --strict    exit with status 1 when any title is topic-only
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence

# Words that make a title a sentence on their own: auxiliaries and modals.
AUXILIARIES = {
    "is", "are", "was", "were", "be", "been", "being", "am", "has", "have", "had",
    "do", "does", "did", "will", "would", "can", "could", "should", "must", "may",
    "might", "shall", "isn't", "aren't", "won't", "can't", "doesn't", "don't",
}

# Base forms of verbs common in case-deck titles; -s, -es, -ed and -ing forms count too.
VERB_BASES = {
    "add", "beat", "boost", "build", "capture", "change", "close", "create",
    "cut", "decline", "deliver", "double", "drive", "drop", "earn", "enable", "expand",
    "fall", "fail", "fix", "gain", "generate", "give", "grow", "halve", "help", "hold",
    "improve", "increase", "lack", "lag", "lead", "lift", "lose", "lower", "make",
    "miss", "move", "need", "offer", "outperform", "own", "pay", "raise", "reach",
    "reduce", "remain", "resist", "return", "rise", "save", "scale", "shift", "show",
    "shrink", "slow", "solve", "stall", "take", "trail", "triple", "unlock", "win",
}
IRREGULAR = {
    "built", "made", "took", "won", "lost", "led", "fell", "rose", "grew", "drove",
    "gave", "paid", "held", "shrank", "grown", "given", "taken",
}

NUMBER = re.compile(r"\d|[₹$€£%]")
WORD = re.compile(r"[a-z']+")


def _verb_forms(base: str) -> set[str]:
    stem = base[:-1] if base.endswith("e") else base
    forms = {base, base + "s", base + "es", stem + "ed", stem + "ing", base + "d"}
    if re.fullmatch(r".*[^aeiou][aeiou][bdgmnpt]", base):  # cut -> cutting, drop -> dropped
        forms |= {base + base[-1] + "ed", base + base[-1] + "ing"}
    return forms


VERBS = AUXILIARIES | IRREGULAR | {f for b in VERB_BASES for f in _verb_forms(b)}


def is_topic_only(title: str) -> bool:
    """True when a title has no number and no verb, so it names a topic only."""
    if NUMBER.search(title):
        return False
    return not any(word in VERBS for word in WORD.findall(title.lower()))


def pptx_titles(path: str | Path) -> list[tuple[int, str]]:
    """(slide number, title) for each slide whose title placeholder holds text."""
    from pptx import Presentation

    found = []
    for number, slide in enumerate(Presentation(str(path)).slides, 1):
        shape = slide.shapes.title
        text = " ".join(shape.text_frame.text.split()) if shape is not None else ""
        if text:
            found.append((number, text))
    return found


def pdf_title(words: Sequence[dict], page_height: float, top_share: float = 0.3) -> str:
    """The largest type in the top part of a page, read left to right, line by line.

    Each word is a pdfplumber word dict with text, size, top and x0.
    """
    top = [w for w in words if w["top"] < page_height * top_share]
    if not top:
        return ""
    biggest = max(w["size"] for w in top)
    title = [w for w in top if abs(w["size"] - biggest) < 0.5]
    title.sort(key=lambda w: (round(w["top"]), w["x0"]))
    return " ".join(w["text"] for w in title)


def pdf_titles(path: str | Path) -> list[tuple[int, str]]:
    """(page number, title) for each page of a PDF deck that has text near the top."""
    import pdfplumber

    found = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            title = pdf_title(page.extract_words(extra_attrs=["size"]), float(page.height))
            if title:
                found.append((number, title))
    return found


def read_titles(path: str | Path) -> list[tuple[int, str]]:
    return pptx_titles(path) if Path(path).suffix.lower() == ".pptx" else pdf_titles(path)


def format_titles(titles: Sequence[tuple[int, str]]) -> str:
    """The ghost deck: one title per line, topic-only ones marked, then a count."""
    flagged = [n for n, t in titles if is_topic_only(t)]
    lines = [f"{'TOPIC' if is_topic_only(t) else '     '} {n:>2} | {t}" for n, t in titles]
    lines.append(f"{len(flagged)} of {len(titles)} titles are topic-only")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List topic-only slide titles.")
    parser.add_argument("deck", help="the deck as a PDF or .pptx")
    parser.add_argument("--strict", action="store_true",
                        help="exit with status 1 when any title is topic-only")
    args = parser.parse_args(argv)
    if not Path(args.deck).is_file():
        parser.error(f"no such file: {args.deck}")
    titles = read_titles(args.deck)
    print(format_titles(titles))
    return 1 if args.strict and any(is_topic_only(t) for _, t in titles) else 0


if __name__ == "__main__":
    sys.exit(main())
