import json
import sys
import zipfile

import pytest

pptx = pytest.importorskip("pptx")
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

import morph

W, H = Inches(13.333), Inches(7.5)


def _deck(path):
    """Three slides: a title and a card that move, a note that only exists on slide 2."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    blank = prs.slide_layouts[6]
    for n, (x, note) in enumerate([(1, None), (6, "Only here"), (8, None)], 1):
        s = prs.slides.add_slide(blank)
        title = s.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(9), Inches(1))
        title.text_frame.text = "Revenue grows 20% a year"
        title.name = "Title %d" % n
        card = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(2), Inches(3), Inches(2))
        card.fill.solid()
        card.text_frame.text = "Card"
        if note:
            box = s.shapes.add_textbox(Inches(1), Inches(5), Inches(4), Inches(1))
            box.text_frame.paragraphs[0].add_run().text = note
            box.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
    prs.save(path)
    return path


def _run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["morph.py", *map(str, argv)])
    return morph.main()


def _slide_xml(path, n):
    with zipfile.ZipFile(path) as z:
        return z.read("ppt/slides/slide%d.xml" % n).decode()


# -------------------------------------------------------------- helpers ---

def test_parse_slides_ranges_and_bounds():
    assert morph.parse_slides("2-4,7,9", 8) == {2, 3, 4, 7}


def test_offcanvas():
    assert morph.offcanvas([-200, 0, 100, 100, 0], 1000, 500)
    assert morph.offcanvas([1000, 0, 100, 100, 0], 1000, 500)
    assert not morph.offcanvas([950, 0, 100, 100, 0], 1000, 500)


class _C:
    def __init__(self, box):
        self.box = box


def test_push_parks_the_whole_block_one_slide_width_away():
    a, b = _C([100, 100, 200, 100, 0]), _C([600, 300, 200, 100, 0])
    off = morph.shifts([a, b], 1000, 500, "push", "right", 1)
    assert off[id(a)] == off[id(b)] == (1020.0, 0)
    for c in (a, b):
        assert morph.offcanvas([c.box[0] + off[id(c)][0], c.box[1], *c.box[2:]], 1000, 500)


def test_assemble_uses_each_components_nearest_edge():
    left, bottom = _C([10, 200, 100, 50, 0]), _C([450, 440, 100, 50, 0])
    off = morph.shifts([left, bottom], 1000, 500, "assemble", "right", 1)
    assert off[id(left)][1] == 0 and off[id(left)][0] < 0
    assert off[id(bottom)][0] == 0 and off[id(bottom)][1] > 0


# ------------------------------------------------------------ end to end ---

def test_plan_writes_nothing_and_pairs_by_text(tmp_path, monkeypatch):
    deck = _deck(tmp_path / "deck.pptx")
    before = deck.read_bytes()
    report = tmp_path / "r.json"
    assert _run(monkeypatch, "plan", deck, "--report", report) == 0
    assert deck.read_bytes() == before
    rep = json.loads(report.read_text())
    assert rep["summary"]["transitions"] == 2
    first = rep["pairs"][0]
    assert {m["from"]["text"] for m in first["matches"]} == {"Revenue grows 20% a year", "Card"}
    assert [i["text"] for i in first["enter"]] == ["Only here"]
    assert first["enter"][0]["motion"] == "glide"


def test_apply_sets_morph_parks_copies_and_passes_self_check(tmp_path, monkeypatch):
    deck, out = _deck(tmp_path / "deck.pptx"), tmp_path / "deck-morph.pptx"
    report = tmp_path / "r.json"
    assert _run(monkeypatch, "apply", deck, "-o", out, "--report", report) == 0
    rep = json.loads(report.read_text())
    assert rep["self_check"] == "passed"
    assert "p159:morph" not in _slide_xml(out, 1)
    for n in (2, 3):
        assert 'option="byObject"' in _slide_xml(out, n)

    pkg = morph.Pkg(str(out))
    names = [{c.name for c in morph.walk(morph.slide_comps(pkg, p, n))} for n, p in enumerate(pkg.slides, 1)]
    title = next(n for n in names[0] if n.startswith("!!m") and "Title" in n)
    assert all(title in s for s in names)                 # one name across all three slides
    note = next(n for n in names[1] if "TextBox" in n)
    assert note in names[0] and note in names[2]          # parked on both neighbours
    ghosts = [el for p in (pkg.slides[0], pkg.slides[2])
              for el, _, _ in morph.top_shapes(pkg.xml(p).find("p:cSld/p:spTree", morph.NS))
              if morph.is_ghost(el, pkg.W, pkg.H)]
    assert len(ghosts) == 2


def test_apply_twice_gives_the_same_deck(tmp_path, monkeypatch):
    deck = _deck(tmp_path / "deck.pptx")
    once, twice = tmp_path / "once.pptx", tmp_path / "twice.pptx"
    _run(monkeypatch, "apply", deck, "-o", once, "--report", tmp_path / "a.json")
    _run(monkeypatch, "apply", once, "-o", twice, "--report", tmp_path / "b.json")
    for n in (1, 2, 3):
        assert _slide_xml(once, n) == _slide_xml(twice, n)


def test_strip_undoes_apply(tmp_path, monkeypatch):
    deck, out, clean = _deck(tmp_path / "deck.pptx"), tmp_path / "m.pptx", tmp_path / "c.pptx"
    _run(monkeypatch, "apply", deck, "-o", out, "--report", tmp_path / "r.json")
    assert _run(monkeypatch, "strip", out, "-o", clean) == 0
    for n in (1, 2, 3):
        xml = _slide_xml(clean, n)
        assert "!!m" not in xml and "morph" not in xml
    pkg = morph.Pkg(str(clean))
    assert [len(morph.slide_comps(pkg, p, n)) for n, p in enumerate(pkg.slides, 1)] == [2, 3, 2]


def test_overrides_unlink_and_refuse_a_mismatched_link(tmp_path, monkeypatch):
    deck = _deck(tmp_path / "deck.pptx")
    pkg = morph.Pkg(str(deck))
    s1, s2 = (morph.slide_comps(pkg, p, n) for n, p in ((1, pkg.slides[0]), (2, pkg.slides[1])))
    card1 = next(c for c in s1 if c.text == "Card")
    card2 = next(c for c in s2 if c.text == "Card")
    note = next(c for c in s2 if c.text == "Only here")
    ov = tmp_path / "ov.json"
    ov.write_text(json.dumps({"unlink": [[card1.ref, card2.ref]], "link": [[card1.ref, note.ref]],
                              "no_morph_slides": [3]}))
    report = tmp_path / "r.json"
    _run(monkeypatch, "plan", deck, "--overrides", ov, "--report", report)
    rep = json.loads(report.read_text())
    assert rep["summary"]["transitions"] == 1                    # slide 3 keeps its own transition
    forced = {(m["from"]["text"], m["to"]["text"]): m["why"] for m in rep["pairs"][0]["matches"]}
    assert forced[("Card", "Only here")] == "forced by override"
    assert ("Card", "Card") not in forced


def test_a_link_across_kinds_is_refused(tmp_path, monkeypatch):
    deck = _deck(tmp_path / "deck.pptx")
    ctx = {"diag": 1.0, "threshold": 0.5, "warn": [], "unlink": set(), "ignore": set()}
    pkg = morph.Pkg(str(deck))
    s1, s2 = (morph.slide_comps(pkg, p, n) for n, p in ((1, pkg.slides[0]), (2, pkg.slides[1])))
    s2[0].kind = "pic"                                          # pretend the title became a picture
    ctx["link"] = {(s1[0].ref, s2[0].ref)}
    pairs = morph.match(s1, s2, ctx)
    assert all(b is not s2[0] for _, b, *_ in pairs)
    assert "cannot pair a sp with a pic" in ctx["warn"][0]


def test_not_a_pptx(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "old.pptx"
    bad.write_bytes(b"not a zip")
    assert _run(monkeypatch, "plan", bad, "--report", tmp_path / "r.json") == 2
    assert "re-saved as plain .pptx" in capsys.readouterr().out


def test_compare_spots_a_changed_slide(tmp_path, monkeypatch):
    from PIL import Image
    for side, colour in (("a", "white"), ("b", "white")):
        Image.new("RGB", (40, 20), "white").save(tmp_path / f"{side}-1.png")
        Image.new("RGB", (40, 20), colour if side == "a" else "red").save(tmp_path / f"{side}-2.png")
    assert _run(monkeypatch, "compare", tmp_path / "a-*.png", tmp_path / "a-*.png") == 0
    assert _run(monkeypatch, "compare", tmp_path / "a-*.png", tmp_path / "b-*.png") == 1
