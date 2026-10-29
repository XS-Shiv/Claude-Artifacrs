"""Count a tweet's length the way X does.

X does not count code points. It follows twitter-text's v3 rules:

- a link counts as 23, however long it is;
- Latin, Greek, Cyrillic and other scripts below U+1100, plus a few
  punctuation ranges (spaces, dashes, quotes, primes), count as 1;
- everything else counts as 2: CJK, Hangul, most symbols, and "…" too;
- an emoji counts as 2 however many code points build it, so a skin tone,
  a ZWJ family or a flag is still 2.

Text is NFC-normalised first, as X does. The limit is 280.

Usage:
    python x_length.py "some tweet text"
"""
from __future__ import annotations

import re
import sys
import unicodedata
from typing import Iterator

MAX_LENGTH = 280
URL_LENGTH = 23
URL = re.compile(r"https?://\S+")
# Code point ranges that count as 1 (twitter-text v3 config).
LIGHT = ((0x0000, 0x10FF), (0x2000, 0x200D), (0x2010, 0x201F), (0x2032, 0x2037))
ZWJ = 0x200D


def _weight(ch: str) -> int:
    cp = ord(ch)
    return 1 if any(lo <= cp <= hi for lo, hi in LIGHT) else 2


def _is_emoji(cp: int) -> bool:
    return 0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0x2B00 <= cp <= 0x2BFF


def _is_modifier(cp: int) -> bool:
    """Code points that attach to the emoji before them."""
    return (
        cp == 0xFE0F                      # emoji presentation selector
        or cp == 0x20E3                   # keycap
        or 0x1F3FB <= cp <= 0x1F3FF       # skin tones
        or 0xE0020 <= cp <= 0xE007F       # tag sequences (subdivision flags)
    )


def _is_regional(cp: int) -> bool:
    return 0x1F1E6 <= cp <= 0x1F1FF


def segments(text: str) -> Iterator[tuple[str, int]]:
    """Split text into pieces X weighs as a unit, each with its weight.

    A piece is a link, one whole emoji sequence, or a single character, so
    cutting between pieces never splits a link or an emoji.
    """
    text = unicodedata.normalize("NFC", text)
    i = 0
    while i < len(text):
        url = URL.match(text, i)
        if url:
            yield url.group(), URL_LENGTH
            i = url.end()
            continue
        cp = ord(text[i])
        if _is_regional(cp) and i + 1 < len(text) and _is_regional(ord(text[i + 1])):
            yield text[i : i + 2], 2  # a flag
            i += 2
            continue
        if _is_emoji(cp) or (i + 1 < len(text) and ord(text[i + 1]) in (0xFE0F, 0x20E3)):
            j = i + 1
            while j < len(text):
                nxt = ord(text[j])
                if _is_modifier(nxt):
                    j += 1
                elif nxt == ZWJ and j + 1 < len(text) and _is_emoji(ord(text[j + 1])):
                    j += 2
                else:
                    break
            yield text[i:j], 2
            i = j
            continue
        yield text[i], _weight(text[i])
        i += 1


def x_length(text: str) -> int:
    """The length X shows for this text."""
    return sum(weight for _, weight in segments(text))


def fits(text: str, limit: int = MAX_LENGTH) -> bool:
    return x_length(text) <= limit


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: python x_length.py TEXT", file=sys.stderr)
        return 2
    text = " ".join(args)
    n = x_length(text)
    print(f"{n}/{MAX_LENGTH}" + ("" if n <= MAX_LENGTH else f" (over by {n - MAX_LENGTH})"))
    return 0 if n <= MAX_LENGTH else 1


if __name__ == "__main__":
    sys.exit(main())
