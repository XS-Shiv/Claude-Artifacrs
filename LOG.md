# Log

What shipped, newest first.

- 2026-10-15: ppt-designer. `titles.py` prints a deck's slide titles in order and marks the topic-only ones (no number, no verb), from `.pptx` title placeholders or the largest type at the top of a PDF page, with `--strict` and tests. [`projects/ppt-designer/`](projects/ppt-designer)
- 2026-10-14: ppt-designer. `deck_reader.py` reads `.pptx` decks directly with python-pptx, counting words, pictures and type sizes in text boxes, groups and tables, with tests. [`projects/ppt-designer/`](projects/ppt-designer)
- 2026-10-13: ppt-designer. `deck_reader.py --format json|csv` prints each slide's measurements and flags in a machine-readable form, with `--no-header` to stack several decks into one CSV. [`projects/ppt-designer/`](projects/ppt-designer)
- 2026-10-12: ppt-designer. Added the skill's web page and `build_page.py`, which generates it from `SKILL.md` so the two cannot drift apart. [`projects/ppt-designer/site/`](projects/ppt-designer/site)
- 2026-10-12: ppt-designer. `deck_reader.py` now lists slides over the skill's limits (type under 8pt, more than 450 words), and `--strict` fails the run when any slide is over. [`projects/ppt-designer/`](projects/ppt-designer)
- 2026-10-12: ppt-designer. Added the skill and `deck_reader.py`, which measures words, images and type sizes on every slide of a PDF deck, with tests. [`projects/ppt-designer/`](projects/ppt-designer)
