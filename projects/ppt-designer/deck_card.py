"""Draft a deck card for the skill's pattern library from a deck's measurements.

The skill's Learn mode turns each reference deck into a deck card. The counting
parts of a card (slides, words per content slide, the arc of titles, weak spots
that the checks can see) come straight from deck_reader.py and titles.py. The
parts that need eyes on the slides (layout, what makes it work, what to borrow)
are left as prompts to fill in from the rendered images.

Usage:
    python deck_card.py deck.pptx
    python deck_card.py deck.pdf --name "Retail case (kirana vs quick commerce)" --result "finalist"
    python deck_card.py deck.pptx --render slides/   also save every slide as slides/s-<n>.jpg
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Sequence

import deck_reader as dr
import titles as tt

WIDTH = 112
FILL_IN = "(fill in from the slide images)"
ARC_WORDS = 6  # each title is cut to this many words in the arc


def _short(title: str, words: int = ARC_WORDS) -> str:
    parts = title.split()
    return " ".join(parts[:words]) + ("..." if len(parts) > words else "")


def arc(titles: Sequence[tuple[int, str]]) -> str:
    """The deck's storyline: titles in slide order, shortened, joined with '>'."""
    return " > ".join(_short(t) for _, t in titles) or "(no titles found)"


def weak_spots(
    slides: Sequence[dr.SlideStats], titles: Sequence[tuple[int, str]]
) -> list[str]:
    """What the checks can see: topic-only titles, small type and overlong slides."""
    spots = []
    topic = [n for n, t in titles if tt.is_topic_only(t)]
    if topic:
        spots.append(f"{len(topic)} of {len(titles)} titles are topic-only "
                     f"(slides {', '.join(map(str, topic))})")
    small = [s.number for s in slides if s.words and s.smallest_pt < dr.MIN_TYPE_PT]
    if small:
        spots.append(f"type under {dr.MIN_TYPE_PT:g}pt on slides {', '.join(map(str, small))}")
    long = [s.number for s in slides if s.words > dr.MAX_WORDS]
    if long:
        spots.append(f"over {dr.MAX_WORDS} words on slides {', '.join(map(str, long))}")
    return spots


def _slide_number(path: Path) -> int:
    match = re.search(r"-(\d+)$", path.stem)
    return int(match.group(1)) if match else 0


def slide_images(out_dir: str | Path) -> list[Path]:
    """The s-<n>.jpg files pdftoppm wrote, in slide order (it pads n on long decks)."""
    return sorted(Path(out_dir).glob("s-*.jpg"), key=_slide_number)


def pptx_to_pdf(path: str | Path, work_dir: str | Path) -> Path:
    """Export a .pptx to PDF with LibreOffice, so pdftoppm can render it."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        raise RuntimeError("LibreOffice was not found; install it or export the deck to PDF")
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(work_dir), str(path)],
        check=True, capture_output=True,
    )
    pdf = Path(work_dir) / (Path(path).stem + ".pdf")
    if not pdf.is_file():
        raise RuntimeError(f"LibreOffice did not export {Path(path).name} to PDF")
    return pdf


def render(deck: str | Path, out_dir: str | Path) -> list[Path]:
    """Save every slide of a PDF or .pptx into out_dir as JPEG and return the files."""
    if Path(deck).suffix.lower() != ".pptx":
        dr.render_slides(deck, out_dir)
    else:
        with tempfile.TemporaryDirectory() as work:
            dr.render_slides(pptx_to_pdf(deck, work), out_dir)
    return slide_images(out_dir)


def _field(label: str, value: str) -> list[str]:
    return textwrap.wrap(f"{label}: {value}", WIDTH, subsequent_indent="  ") or [f"{label}:"]


def build_card(
    name: str,
    slides: Sequence[dr.SlideStats],
    titles: Sequence[tuple[int, str]],
    result: str = "not stated",
    images: Sequence[Path] = (),
) -> str:
    content = dr.content_slides(slides)
    median = dr.median_words(slides)
    counts = f"Slides: {len(slides)} ({len(content)} content)"
    if median is not None:
        counts += f"   Words per content slide: about {round(median, -1):.0f}"
    spots = weak_spots(slides, titles)
    fill_in = FILL_IN
    if images:
        fill_in = f"(fill in from the slide images in {Path(images[0]).parent}/)"
    lines = [
        *_field("Deck", name),
        f"Result: {result:<34} {counts}",
        *_field("Arc", arc(titles)),
        *_field("Layout", fill_in),
        *_field("What makes it work", fill_in),
        *_field("Worth borrowing", fill_in),
        *_field("Weak spots", "; ".join(spots) if spots else "none found by the checks"),
    ]
    return "```\n" + "\n".join(lines) + "\n```"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draft a deck card from a deck's measurements.")
    parser.add_argument("deck", help="the deck as a PDF or .pptx")
    parser.add_argument("--name", help="what the deck is (defaults to the file name)")
    parser.add_argument("--result", default="not stated", help="how the deck placed, if known")
    parser.add_argument("--render", metavar="DIR",
                        help="also save every slide into DIR as s-<n>.jpg (a .pptx needs LibreOffice)")
    args = parser.parse_args(argv)
    if not Path(args.deck).is_file():
        parser.error(f"no such file: {args.deck}")
    images: list[Path] = []
    if args.render:
        try:
            images = render(args.deck, args.render)
        except (RuntimeError, subprocess.CalledProcessError) as err:
            print(f"deck_card.py: could not render slides: {err}", file=sys.stderr)
            return 2
    card = build_card(args.name or Path(args.deck).stem, dr.read_deck(args.deck),
                      tt.read_titles(args.deck), args.result, images)
    print(card)
    if images:
        print(f"Saved {len(images)} slide images in {args.render}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
