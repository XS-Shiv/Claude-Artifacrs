# ppt-designer

A Claude skill for building and critiquing presentation decks (it started with case competitions, and the skill file is still named `case-comp-deck-designer`), plus small tools that check a deck slide by slide: how dense it is and whether its titles state a conclusion.

## What's here

| File | What it is |
|---|---|
| `SKILL.md` | The skill: a playbook for decoding a brief, building the argument and laying out the deck, plus a pattern library of what strong decks look like |
| `deck_reader.py` | Measures a PDF or `.pptx` deck: words, images, body type size and smallest type size on every slide |
| `titles.py` | Lists slide titles that name a topic instead of stating a conclusion |
| `deck_card.py` | Drafts a deck card for the skill's pattern library from those measurements |
| `site/index.html` | The skill as a web page, with a button that copies the skill file |
| `build_page.py` | Builds `site/index.html` from `SKILL.md` and `page_template.html` |
| `tests/` | Tests for the reader, the title check, the deck card and the page builder |

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

To compare decks, print the measurements as JSON or CSV instead of the table. Both include each slide's flags, and `--strict` works the same way. CSV puts the deck's file name in every row, so `--no-header` lets several decks be stacked into one file:

```bash
python deck_reader.py deck.pdf --format json
python deck_reader.py ours.pdf --format csv > decks.csv
python deck_reader.py winner.pdf --format csv --no-header >> decks.csv
```

```
deck,slide,words,images,body_pt,smallest_pt,content,flags
ours.pdf,1,3,0,40.0,40.0,False,
ours.pdf,2,88,1,12.0,6.7,True,"type at 6.7pt, under the 8pt floor"
```

To also save every slide as an image, add a folder name. This needs [poppler](https://poppler.freedesktop.org/) installed.

```bash
python deck_reader.py deck.pdf slides/
```

A `.pptx` can be read directly, with no PDF export:

```bash
python deck_reader.py deck.pptx --strict
```

Words, pictures and type sizes are read from text boxes, groups and tables. A run that sets no size of its own or on its paragraph is counted at 18pt, PowerPoint's default, because sizes inherited from the slide master are not looked up. Rendering slides to images still needs a PDF.

## Checking titles

The skill asks for action titles: a full sentence with a verb, and a number where one exists. `titles.py` prints the deck's titles in order (the ghost deck) and marks the ones that are topic-only, meaning no number and no verb:

```bash
python titles.py deck.pptx
python titles.py deck.pdf --strict
```

```
TOPIC  1 | Market overview
       2 | Chennai resists quick commerce but offers a first-mover advantage
TOPIC  3 | Financials
2 of 3 titles are topic-only
```

In a `.pptx` the title is the slide's title placeholder; in a PDF it is the largest type in the top 30% of the page. Verbs are matched against a word list rather than parsed, so a title it flags is almost always a topic label, while an unusual verb can let a topic title pass. `--strict` exits with status 1 when any title is topic-only.

## Drafting a deck card

In Learn mode the skill turns each reference deck into a deck card. `deck_card.py` fills in the parts that can be counted, in the card's own format, and leaves the parts that need eyes on the slides as prompts:

```bash
python deck_card.py deck.pptx --name "Sample retail case" --result finalist
```

```
Deck: Sample retail case
Result: finalist                           Slides: 4 (2 content)   Words per content slide: about 220
Arc: Market entry plan > Chennai resists quick commerce but offers... > Financials > Thank you
Layout: (fill in from the slide images)
What makes it work: (fill in from the slide images)
Worth borrowing: (fill in from the slide images)
Weak spots: 3 of 4 titles are topic-only (slides 1, 3, 4)
```

The arc is the slide titles in order, each cut to six words. Weak spots list what `deck_reader.py` and `titles.py` can see: topic-only titles, type under 8pt and slides over 450 words. `--name` defaults to the file name and `--result` to "not stated".

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
