# ppt-transition

A Claude skill that adds PowerPoint Morph transitions between the slides of a finished `.pptx`, component by component, plus the engine behind it. Components that appear on both slides travel, resize and re-word into their new state; everything else glides on or off instead of popping. The result is a normal, editable deck: no video, no add-ins.

## What's here

| File | What it is |
|---|---|
| `SKILL.md` | The skill: how Morph pairs objects, the plan, check, apply workflow, and the limits to tell the user about |
| `morph.py` | The engine, extracted unchanged from the skill: `plan`, `apply`, `strip`, `storyboard`, `compare` |
| `tests/` | Tests that build small decks with python-pptx and run the engine end to end, plus `test_score.py`, which checks the matching score on hand-built pairs |

## How it works

Morph only animates an object it believes is on both slides, and its own guesses are unreliable. Two objects of the same type whose names start with `!!` and match always morph into each other. So the engine:

1. **Pairs** each component with its counterpart on the next slide (same text, same image, same placeholder, a one-of-a-kind look, or the same place and size) and gives each pair a shared `!!m` name.
2. **Parks a copy** of every unpaired component just off the edge of the neighbouring slide under the same name, so Morph glides it in or out. The copies are invisible in the show.
3. **Sets the Morph transition** on each slide, keeping any auto-advance timing.

## Running it

```bash
pip install -r requirements.txt
python morph.py plan deck.pptx                       # writes nothing; prints and saves the pairing report
python morph.py apply deck.pptx -o deck-morph.pptx   # writes the animated copy
python morph.py strip deck-morph.pptx -o clean.pptx  # undoes it
python morph.py apply deck.pptx -o deck-morph.pptx --dry-run   # writes no deck; prints a table of changes
```

`--dry-run` on the same sample:

```
DRY RUN (nothing written)  |  2 transitions
slides  morph  glide   fade   weak
----------------------------------
1 -> 2      2      1      0      0
2 -> 3      2      1      0      0
----------------------------------
total       4      2      0      0
```

Weak matches, if any, are listed under the table with their scores, so they can be fixed with an overrides file before the real run.

Output for a three-slide sample where a title and a card move and a note appears only on slide 2:

```
APPLIED -> deck-morph.pptx  |  2 transitions  |  4 components morph, 2 glide in/out, 0 fade
  slide 1 -> 2: 2 morph, 1 glide, 0 fade
  slide 2 -> 3: 2 morph, 1 glide, 0 fade
  self-check: passed
```

`--style push|assemble|fade`, `--enter-from`, `--duration`, `--text-mode object|word|char` and `--slides 2-6,9` set the feel. Wrong pairs are fixed with an overrides file (`link`, `unlink`, `ignore`, `no_morph_slides`, `text_mode`); `SKILL.md` explains each one.

Running `apply` on an already processed deck rebuilds it from scratch, so it is safe to edit the morphed deck and run it again.

## Tests

```bash
pytest
```

The tests check the pairing report, that `apply` names each pair the same across slides and parks copies off the canvas, that applying twice gives the same deck, that `strip` restores the original, that overrides are honoured, that `--dry-run` counts each transition's changes without writing a deck, and that `SKILL.md` carries the same engine as `morph.py`. `tests/test_score.py` feeds the matching score hand-built pairs (same text, a moved shape, the same image, footers, retitled slides) and checks which clear the default 0.5 threshold.

## Where this came from

Built as a Claude skill first. `morph.py` started as the engine block from `SKILL.md` (sha256 `4683ad8936dd`). Changes are made here and copied back into the skill's block, and a test fails if the two differ or the sha256 in `SKILL.md` is out of date.
