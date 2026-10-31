# dailypush-x

A Claude skill I wrote that makes one day of X threads: two a day, 3 to 5 tweets each. Slot A threads one of my S or A tier Medium essays; slot B threads a current product, design or AI story. Each piece goes through brainstorm, draft and audit, and only a fully passing audit puts it in the posting queue. The skill never posts to X itself.

| Path | What it is |
|---|---|
| `SKILL.md` | The skill: inputs, the day folder layout, and the brainstorm, draft, audit, record and hand-off steps |
| `scripts/check_thread.py` | The audit's mechanical checks on a `thread.json`: 3 to 5 tweets, 280 as X counts, one link in the last tweet only, no hashtags, emojis, numbering or em dashes, no empty or repeated tweets |
| `scripts/render_svg.js` | Renders the thread's SVG illustration to the 1600x900 PNG attached to tweet 1, refusing any `<text>` |
| `references/` | Thread format and house style, the audit checklist, the Medium tier rubric, research sources and the library template |

## Checking a thread

```bash
python scripts/check_thread.py day-3/piece-1-medium/thread.json
```

```
  tweet 1: 74 chars
  ...
PASS — 3 to 5 tweets
PASS — every tweet <= 280 (X counting)
PASS — one link, last tweet only
PASS — no hashtags, emojis, numbering or em dashes
PASS — no empty or duplicate tweets
```

It exits 1 when any check fails and 2 when the file is not a `thread.json`.

## Rendering the image

```bash
NODE_PATH=$(npm root -g) node scripts/render_svg.js images/hook.svg images/hook.png
```

It uses Playwright's Chromium, defaults to 1600x900 (pass a width and height to change it), creates the output folder, exits 1 when the SVG holds `<text>` and 2 when the file is not an SVG.

## Tests

```bash
pip install -r requirements.txt
NODE_PATH=$(npm root -g) pytest
```

The render tests are skipped when node or its Playwright is not installed.

The steps that need no model are being moved into small, tested scripts, one at a time; see `BACKLOG.md` at the repo root.
