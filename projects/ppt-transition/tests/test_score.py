"""The matching score on hand-built pairs, without building a deck.

score() only reads a few attributes, so plain namespaces stand in for Comp.
THRESHOLD is the CLI default: a pair at or above it becomes a Morph pair.
"""
import math
from types import SimpleNamespace

import pytest

import morph

W, H = 12192000, 6858000          # 13.333 x 7.5 in, in EMU
DIAG = math.hypot(W, H)
THRESHOLD = 0.5
IN = 914400


def comp(kind="sp", text="", box=(1, 1, 3, 2), **kw):
    fields = dict(kind=kind, ph=None, ph_idx=None, text=text, img="", geom="", fill="", name="",
                  box=[int(v * IN) for v in box] + [0] if box else None)
    fields.update(kw)
    return SimpleNamespace(**fields)


def test_same_text_same_place_is_a_confident_pair():
    a = comp(text="Revenue grows 20% a year", box=(0.5, 0.4, 9, 1))
    sc, why = morph.score(a, comp(text="Revenue grows 20% a year", box=(0.5, 0.4, 9, 1)), DIAG)
    assert sc == pytest.approx(1.0)
    assert "same text" in why and "same place" in why


def test_same_text_moved_still_pairs_but_scores_lower():
    a = comp(text="Revenue grows 20% a year", box=(0.5, 0.4, 9, 1))
    still, _ = morph.score(a, comp(text="Revenue grows 20% a year", box=(0.5, 0.4, 9, 1)), DIAG)
    moved, why = morph.score(a, comp(text="Revenue grows 20% a year", box=(0.5, 5.5, 9, 1)), DIAG)
    assert THRESHOLD <= moved < still
    assert "same size, moved" in why


def test_moved_shape_with_no_text_pairs_on_look_and_size():
    a = comp(geom="roundRect", fill="solidFill:schemeClr=accent1", box=(1, 2, 3, 2))
    sc, why = morph.score(a, comp(geom="roundRect", fill="solidFill:schemeClr=accent1", box=(6, 2, 3, 2)), DIAG)
    assert sc < THRESHOLD           # on its own, a plain card is not enough ...
    assert "same size, moved" in why
    near, _ = morph.score(a, comp(geom="roundRect", fill="solidFill:schemeClr=accent1", box=(2, 2, 3, 2)), DIAG)
    assert near > sc                # ... but closer is more likely the same card


def test_same_image_pairs_even_when_resized_and_moved():
    a = comp(kind="pic", img="ab12cd34ef56", box=(9, 0.3, 3, 1))
    sc, why = morph.score(a, comp(kind="pic", img="ab12cd34ef56", box=(0.5, 6.5, 1.5, 0.5)), DIAG)
    assert sc >= THRESHOLD
    assert "same image" in why


def test_different_images_in_the_same_slot_do_not_pair():
    a = comp(kind="pic", img="ab12cd34ef56", box=(1, 1, 4, 3))
    sc, _ = morph.score(a, comp(kind="pic", img="0000ffff1111", box=(1, 1, 4, 3)), DIAG)
    assert sc < THRESHOLD


def test_footer_pairs_only_with_the_same_footer_kind():
    num = comp(ph="sldNum", text="3", box=(12, 7, 0.8, 0.3))
    assert morph.score(num, comp(ph="sldNum", text="4", box=(12, 7, 0.8, 0.3)), DIAG) == (0.9, "same footer placeholder")
    assert morph.score(num, comp(ph="ftr", text="3", box=(12, 7, 0.8, 0.3)), DIAG) == (0.0, "")
    assert morph.score(num, comp(text="3", box=(12, 7, 0.8, 0.3)), DIAG)[0] == 0.0


def test_titles_pair_even_when_the_wording_changes():
    a = comp(ph="title", text="Where we are", box=(0.5, 0.4, 9, 1))
    sc, why = morph.score(a, comp(ph="title", text="Where we go next", box=(0.5, 0.4, 9, 1)), DIAG)
    assert sc >= THRESHOLD
    assert why.startswith("both are the slide title")


def test_different_kinds_never_pair():
    assert morph.score(comp(text="Q3"), comp(kind="pic", text="Q3"), DIAG) == (0.0, "")


def test_score_is_capped_at_one():
    kw = dict(text="Revenue", img="ab12", geom="rect", fill="solidFill:x", name="Hero", box=(1, 1, 3, 2))
    assert morph.score(comp(**kw), comp(**kw), DIAG)[0] == 1.0
