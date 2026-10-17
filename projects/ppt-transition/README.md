# ppt-transition

A Claude skill that adds PowerPoint Morph transitions between the slides of a finished `.pptx`, component by component, plus the engine behind it. Components that appear on both slides travel, resize and re-word into their new state; everything else glides on or off instead of popping. The result is a normal, editable deck: no video, no add-ins.

## What's here

| File | What it is |
|---|---|
| `SKILL.md` | The skill: how Morph pairs objects, the plan, check, apply workflow, and the limits to tell the user about |
| `morph.py` | The engine, extracted unchanged from the skill: `plan`, `apply`, `strip`, `storyboard`, `compare` |
| `tests/` | Tests that build small decks with python-pptx and run the engine end to end |

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
```

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

The tests check the pairing report, that `apply` names each pair the same across slides and parks copies off the canvas, that applying twice gives the same deck, that `strip` restores the original, and that overrides are honoured.

## Where this came from

Built as a Claude skill first. `morph.py` is the engine block from `SKILL.md`, extracted byte for byte (sha256 starts `4683ad8936dd`); later changes will be made here and carried back into the skill.
