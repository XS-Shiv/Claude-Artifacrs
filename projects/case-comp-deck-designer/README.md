# case-comp-deck-designer

A Claude skill for building and critiquing case-competition decks, and a small tool that measures how dense a deck is, slide by slide.

## What's here

| File | What it is |
|---|---|
| `SKILL.md` | The skill: a playbook for decoding a brief, building the argument and laying out the deck, plus a pattern library of what strong decks look like |
| `deck_reader.py` | Measures a PDF deck: words, images, body type size and smallest type size on every slide |
| `site/index.html` | The skill as a web page, with a button that copies the skill file |
| `build_page.py` | Builds `site/index.html` from `SKILL.md` and `page_template.html` |
| `tests/` | Tests for the reader and the page builder |

## Measuring a deck

```bash
pip install -r requirements.txt
python deck_reader.py deck.pdf
```

Output for a four-slide sample:

```
4 slides, 2 content slides, median 271 words per content slide
 1 |    3 words |  0 images | body 40.0pt | smallest 40.0pt
 2 |  231 words |  1 images | body 10.7pt | smallest  8.0pt
 3 |  311 words |  1 images | body 10.7pt | smallest  6.7pt
 4 |    2 words |  0 images | body 40.0pt | smallest 40.0pt
Over the limits:
  slide 3: type at 6.7pt, under the 8pt floor
```

How to read it:

- A slide with fewer than 60 words counts as a cover, divider or thank-you slide and is left out of the median.
- Type sizes are shown as they would appear on a standard 13.33in-wide slide, so decks exported at different page sizes can be compared.
- A slide is listed under "Over the limits" when it has type smaller than 8pt or more than 450 words. Both limits come from the skill: 8pt is its floor for readable type, and 450 words is the densest content slide in its reference decks.

To use it as a check before submitting, add `--strict`, which exits with status 1 when any slide is over a limit. The limits can be changed, for example for a deck that will be presented live:

```bash
python deck_reader.py deck.pdf --strict
python deck_reader.py deck.pdf --strict --min-type 12 --max-words 120
```

To also save every slide as an image, add a folder name. This needs [poppler](https://poppler.freedesktop.org/) installed.

```bash
python deck_reader.py deck.pdf slides/
```

A `.pptx` has to be exported to PDF first.

## Using the skill

Paste the contents of `SKILL.md` into a chat with Claude and ask it to save it as a skill. Then attach a case and ask for a deck, attach a draft and ask for a critique, or attach finished decks and ask it to learn from them.

## The skill's page

Open `site/index.html` in a browser to read the skill as a page and copy it with one click.

The page is generated, so do not edit it by hand. After changing `SKILL.md` or `page_template.html`, rebuild it:

```bash
python build_page.py
```

`python build_page.py --check` exits with status 1 if the page no longer matches the skill. The tests run the same check, so a stale page fails the suite.

## Tests

```bash
pytest
```

## Where this came from

The skill and its page were first built as a Claude artifact. `deck_reader.py` started as the short script inside the skill's Learn mode; this version prints the same numbers, makes the image rendering optional, and handles a deck with no content slides, which the original script crashed on.
