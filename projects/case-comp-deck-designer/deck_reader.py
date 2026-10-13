"""Measure a slide deck saved as PDF: words, images and type sizes on every slide.

Type sizes are reported as they would appear on a standard 13.33in-wide slide,
so decks exported at different page sizes can be compared with each other.

Slides that break a readability limit are listed under the table: type smaller than
8pt, or more than 450 words. Both limits come from the skill in SKILL.md.

Usage:
    python deck_reader.py deck.pdf            print the table and any slides over the limits
    python deck_reader.py deck.pdf out_dir    also render every slide into out_dir as JPEG
    python deck_reader.py deck.pdf --strict   exit with status 1 when a slide is over a limit
    python deck_reader.py deck.pdf --format json   (or csv) print machine-readable output
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

SLIDE_WIDTH_PT = 960.0  # a 13.33in-wide slide at 72 points per inch
CONTENT_MIN_WORDS = 60  # fewer words than this is a cover, divider or thank-you slide
MIN_TYPE_PT = 8.0  # the skill's floor: smaller type cannot be read on a slide
MAX_WORDS = 450  # the densest content slides in the skill's reference decks


@dataclass(frozen=True)
class SlideStats:
    number: int
    words: int
    images: int
    body_pt: float  # median type size on the slide
    smallest_pt: float


def scale_to_slide(size_pt: float, page_width_pt: float) -> float:
    """Convert a type size on a page of any width to its size on a standard slide."""
    if page_width_pt <= 0:
        raise ValueError("page width must be positive")
    return size_pt * SLIDE_WIDTH_PT / page_width_pt


def slide_stats(
    number: int, word_sizes: Iterable[float], page_width_pt: float, images: int = 0
) -> SlideStats:
    """Summarise one slide from the type size of each of its words."""
    sizes = [scale_to_slide(size, page_width_pt) for size in word_sizes]
    if not sizes:
        return SlideStats(number, 0, images, 0.0, 0.0)
    return SlideStats(number, len(sizes), images, statistics.median(sizes), min(sizes))


def content_slides(
    slides: Sequence[SlideStats], min_words: int = CONTENT_MIN_WORDS
) -> list[SlideStats]:
    """Drop covers, dividers and thank-you slides, which carry too few words to count."""
    return [slide for slide in slides if slide.words >= min_words]


def median_words(slides: Sequence[SlideStats]) -> float | None:
    """Median words per content slide, or None when the deck has no content slides."""
    counts = [slide.words for slide in content_slides(slides)]
    return statistics.median(counts) if counts else None


def read_pdf(path: str | Path) -> list[SlideStats]:
    """Read every page of a PDF deck into SlideStats."""
    import pdfplumber  # imported here so the functions above work without it installed

    slides = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            words = page.extract_words(extra_attrs=["size"])
            sizes = [word["size"] for word in words]
            slides.append(slide_stats(number, sizes, float(page.width), len(page.images)))
    return slides


def render_slides(path: str | Path, out_dir: str | Path, width_px: int = 1280) -> None:
    """Write every slide into out_dir as s-<n>.jpg, using poppler's pdftoppm."""
    if shutil.which("pdftoppm") is None:
        raise RuntimeError("pdftoppm was not found; install poppler to render slides")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pdftoppm", "-scale-to-x", str(width_px), "-scale-to-y", "-1", "-jpeg",
         str(path), str(out / "s")],
        check=True,
    )


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def format_report(slides: Sequence[SlideStats]) -> str:
    """One summary line, then one line per slide."""
    median = median_words(slides)
    summary = f"{_count(len(slides), 'slide')}, {_count(len(content_slides(slides)), 'content slide')}"
    if median is not None:
        summary += f", median {median:.0f} words per content slide"
    lines = [summary]
    for s in slides:
        lines.append(
            f"{s.number:>2} | {s.words:>4} words | {s.images:>2} images"
            f" | body {s.body_pt:4.1f}pt | smallest {s.smallest_pt:4.1f}pt"
        )
    return "\n".join(lines)


def slide_flags(
    slide: SlideStats, min_type_pt: float = MIN_TYPE_PT, max_words: int = MAX_WORDS
) -> list[str]:
    """The readability limits one slide breaks, as short phrases. Empty when it breaks none."""
    flags = []
    # compare the size as the report prints it, so 7.96pt shows and counts as 8.0pt
    if slide.words and round(slide.smallest_pt, 1) < min_type_pt:
        flags.append(f"type at {slide.smallest_pt:.1f}pt, under the {min_type_pt:g}pt floor")
    if slide.words > max_words:
        flags.append(f"{slide.words} words, over the {max_words}-word limit")
    return flags


def format_flags(
    slides: Sequence[SlideStats], min_type_pt: float = MIN_TYPE_PT, max_words: int = MAX_WORDS
) -> str:
    """One line per broken limit under a heading, or an empty string when nothing is flagged."""
    lines = [
        f"  slide {slide.number}: {flag}"
        for slide in slides
        for flag in slide_flags(slide, min_type_pt, max_words)
    ]
    return "\n".join(["Over the limits:", *lines]) if lines else ""


CSV_FIELDS = ["deck", "slide", "words", "images", "body_pt", "smallest_pt", "content", "flags"]


def to_records(
    slides: Sequence[SlideStats], min_type_pt: float = MIN_TYPE_PT, max_words: int = MAX_WORDS
) -> list[dict]:
    """One dict per slide, with sizes rounded as the text report shows them."""
    return [
        {
            "slide": s.number,
            "words": s.words,
            "images": s.images,
            "body_pt": round(s.body_pt, 1),
            "smallest_pt": round(s.smallest_pt, 1),
            "content": s.words >= CONTENT_MIN_WORDS,
            "flags": slide_flags(s, min_type_pt, max_words),
        }
        for s in slides
    ]


def format_json(
    deck: str, slides: Sequence[SlideStats],
    min_type_pt: float = MIN_TYPE_PT, max_words: int = MAX_WORDS,
) -> str:
    """The deck's summary, limits and per-slide measurements as one JSON document."""
    records = to_records(slides, min_type_pt, max_words)
    doc = {
        "deck": deck,
        "slides": len(slides),
        "content_slides": len(content_slides(slides)),
        "median_words": median_words(slides),
        "limits": {"min_type_pt": min_type_pt, "max_words": max_words},
        "flagged_slides": [r["slide"] for r in records if r["flags"]],
        "per_slide": records,
    }
    return json.dumps(doc, indent=2)


def format_csv(
    deck: str, slides: Sequence[SlideStats], min_type_pt: float = MIN_TYPE_PT,
    max_words: int = MAX_WORDS, header: bool = True,
) -> str:
    """One row per slide, with the deck name in every row so several decks can be stacked."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    if header:
        writer.writeheader()
    for record in to_records(slides, min_type_pt, max_words):
        writer.writerow({**record, "deck": deck, "flags": "; ".join(record["flags"])})
    return buf.getvalue().rstrip("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure a PDF slide deck slide by slide.")
    parser.add_argument("deck", help="the deck as a PDF")
    parser.add_argument("out_dir", nargs="?", help="folder to render the slides into as JPEG")
    parser.add_argument("--min-type", type=float, default=MIN_TYPE_PT, metavar="PT",
                        help="flag slides with type smaller than this (default: %(default)g)")
    parser.add_argument("--max-words", type=int, default=MAX_WORDS, metavar="N",
                        help="flag slides with more words than this (default: %(default)s)")
    parser.add_argument("--strict", action="store_true",
                        help="exit with status 1 when any slide is over a limit")
    parser.add_argument("--format", choices=["text", "json", "csv"], default="text",
                        help="output format (default: %(default)s)")
    parser.add_argument("--no-header", action="store_true",
                        help="with --format csv, leave out the header row, to append to a file")
    args = parser.parse_args(argv)
    if not Path(args.deck).is_file():
        parser.error(f"no such file: {args.deck}")
    slides = read_pdf(args.deck)
    if args.out_dir:
        render_slides(args.deck, args.out_dir)
    flags = format_flags(slides, args.min_type, args.max_words)
    name = Path(args.deck).name
    if args.format == "json":
        print(format_json(name, slides, args.min_type, args.max_words))
    elif args.format == "csv":
        print(format_csv(name, slides, args.min_type, args.max_words, not args.no_header))
    else:
        print(format_report(slides))
        if flags:
            print(flags)
    return 1 if flags and args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
