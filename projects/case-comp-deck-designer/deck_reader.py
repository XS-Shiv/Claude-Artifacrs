"""Measure a slide deck saved as PDF: words, images and type sizes on every slide.

Type sizes are reported as they would appear on a standard 13.33in-wide slide,
so decks exported at different page sizes can be compared with each other.

Usage:
    python deck_reader.py deck.pdf            print the table
    python deck_reader.py deck.pdf out_dir    also render every slide into out_dir as JPEG
"""
from __future__ import annotations

import argparse
import shutil
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

SLIDE_WIDTH_PT = 960.0  # a 13.33in-wide slide at 72 points per inch
CONTENT_MIN_WORDS = 60  # fewer words than this is a cover, divider or thank-you slide


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure a PDF slide deck slide by slide.")
    parser.add_argument("deck", help="the deck as a PDF")
    parser.add_argument("out_dir", nargs="?", help="folder to render the slides into as JPEG")
    args = parser.parse_args(argv)
    if not Path(args.deck).is_file():
        parser.error(f"no such file: {args.deck}")
    slides = read_pdf(args.deck)
    if args.out_dir:
        render_slides(args.deck, args.out_dir)
    print(format_report(slides))
    return 0


if __name__ == "__main__":
    sys.exit(main())
