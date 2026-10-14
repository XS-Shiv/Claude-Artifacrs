# Log

What shipped, newest first.

- 2026-10-14: case-comp-deck-designer. `deck_reader.py` reads `.pptx` decks directly with python-pptx, counting words, pictures and type sizes in text boxes, groups and tables, with tests. [`projects/case-comp-deck-designer/`](projects/case-comp-deck-designer)
- 2026-10-13: case-comp-deck-designer. `deck_reader.py --format json|csv` prints each slide's measurements and flags in a machine-readable form, with `--no-header` to stack several decks into one CSV. [`projects/case-comp-deck-designer/`](projects/case-comp-deck-designer)
- 2026-10-12: case-comp-deck-designer. Added the skill's web page and `build_page.py`, which generates it from `SKILL.md` so the two cannot drift apart. [`projects/case-comp-deck-designer/site/`](projects/case-comp-deck-designer/site)
- 2026-10-12: case-comp-deck-designer. `deck_reader.py` now lists slides over the skill's limits (type under 8pt, more than 450 words), and `--strict` fails the run when any slide is over. [`projects/case-comp-deck-designer/`](projects/case-comp-deck-designer)
- 2026-10-12: case-comp-deck-designer. Added the skill and `deck_reader.py`, which measures words, images and type sizes on every slide of a PDF deck, with tests. [`projects/case-comp-deck-designer/`](projects/case-comp-deck-designer)
