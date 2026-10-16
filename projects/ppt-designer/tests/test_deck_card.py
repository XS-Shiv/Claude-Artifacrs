import pytest

import deck_card as dc
from deck_reader import SlideStats

SLIDES = [
    SlideStats(1, 4, 0, 40.0, 40.0),     # cover
    SlideStats(2, 312, 1, 10.5, 6.5),    # dense, with tiny type
    SlideStats(3, 480, 2, 9.0, 8.0),     # over the word limit
    SlideStats(4, 2, 0, 40.0, 40.0),     # thank you
]
TITLES = [
    (1, "Market entry plan"),
    (2, "Chennai resists quick commerce but offers a first-mover advantage"),
    (3, "Financials"),
    (4, "Thank you"),
]


def test_arc_shortens_titles_and_keeps_order():
    assert dc.arc(TITLES) == (
        "Market entry plan > Chennai resists quick commerce but offers... > Financials > Thank you"
    )


def test_arc_without_titles():
    assert dc.arc([]) == "(no titles found)"


def test_weak_spots_lists_what_the_checks_see():
    assert dc.weak_spots(SLIDES, TITLES) == [
        "3 of 4 titles are topic-only (slides 1, 3, 4)",
        "type under 8pt on slides 2",
        "over 450 words on slides 3",
    ]


def test_weak_spots_ignores_slides_with_no_text():
    assert dc.weak_spots([SlideStats(1, 0, 3, 0.0, 0.0)], []) == []


def test_card_follows_the_skill_template():
    card = dc.build_card("Sample retail case", SLIDES, TITLES, result="finalist")
    lines = card.splitlines()
    assert lines[0] == lines[-1] == "```"
    assert lines[1] == "Deck: Sample retail case"
    assert lines[2].startswith("Result: finalist ")
    assert lines[2].endswith("Slides: 4 (2 content)   Words per content slide: about 400")
    labels = [line.split(":")[0] for line in lines[1:-1] if not line.startswith("  ")]
    assert labels == ["Deck", "Result", "Arc", "Layout", "What makes it work",
                      "Worth borrowing", "Weak spots"]
    assert f"Layout: {dc.FILL_IN}" in lines
    assert all(len(line) <= dc.WIDTH for line in lines)


def test_card_for_a_clean_deck_with_no_content_slides():
    card = dc.build_card("Tiny", [SlideStats(1, 5, 0, 30.0, 30.0)], [(1, "Revenue grows 20%")])
    assert "Slides: 1 (0 content)\n" in card
    assert "Words per content slide" not in card
    assert "Weak spots: none found by the checks" in card


def test_long_arc_wraps_with_an_indent():
    titles = [(n, f"Section {n} grows revenue by a lot") for n in range(1, 13)]
    lines = dc.build_card("Long", [], titles).splitlines()
    arc_at = next(i for i, line in enumerate(lines) if line.startswith("Arc:"))
    assert lines[arc_at + 1].startswith("  ")


def test_cli_reads_a_pptx(tmp_path, capsys):
    pptx = pytest.importorskip("pptx")
    prs = pptx.Presentation()
    for text in ["Market overview", "Revenue grows 20%"]:
        prs.slides.add_slide(prs.slide_layouts[5]).shapes.title.text = text
    path = tmp_path / "ours.pptx"
    prs.save(path)

    assert dc.main([str(path), "--result", "winner"]) == 0
    out = capsys.readouterr().out
    assert "Deck: ours\n" in out
    assert "Arc: Market overview > Revenue grows 20%" in out
    assert "1 of 2 titles are topic-only (slides 1)" in out


def test_cli_rejects_a_missing_file(tmp_path):
    with pytest.raises(SystemExit):
        dc.main([str(tmp_path / "nope.pdf")])
