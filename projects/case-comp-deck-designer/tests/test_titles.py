import pytest

import titles as tt


@pytest.mark.parametrize("title", [
    "Chennai market analysis",
    "Competitive landscape",
    "SWOT Analysis",
    "Financials",
    "Go-to-market strategy",
])
def test_topic_labels_are_flagged(title):
    assert tt.is_topic_only(title)


@pytest.mark.parametrize("title", [
    "Chennai resists quick commerce but offers a first-mover advantage",
    "Revenue grows 20% a year",
    "Three levers close the gap by FY28",
    "Delivery cost is the real constraint",
    "Tier-2 cities drove most of the growth",
    "Dropping the free tier lifts margin",
    "Payback in ₹ terms",
])
def test_action_titles_pass(title):
    assert not tt.is_topic_only(title)


def test_doubled_consonant_forms_count_as_verbs():
    assert {"cutting", "dropped", "stalled"} <= tt.VERBS


def test_pdf_title_takes_largest_type_near_the_top():
    words = [
        {"text": "Market", "size": 20, "top": 30, "x0": 40},
        {"text": "sizing", "size": 20, "top": 30, "x0": 110},
        {"text": "tracker", "size": 9, "top": 10, "x0": 40},
        {"text": "BIG", "size": 60, "top": 400, "x0": 40},  # a chart label low on the page
    ]
    assert tt.pdf_title(words, page_height=540) == "Market sizing"


def test_pdf_title_reads_two_lines_in_order():
    words = [
        {"text": "margin", "size": 18, "top": 52, "x0": 40},
        {"text": "Pricing", "size": 18, "top": 30, "x0": 40},
        {"text": "lifts", "size": 18, "top": 30, "x0": 100},
    ]
    assert tt.pdf_title(words, page_height=540) == "Pricing lifts margin"


def test_pdf_page_with_nothing_near_the_top_has_no_title():
    assert tt.pdf_title([{"text": "x", "size": 10, "top": 500, "x0": 0}], 540) == ""


def test_format_titles_marks_and_counts():
    out = tt.format_titles([(1, "Market overview"), (2, "Revenue grows 20%")])
    assert out.splitlines() == [
        "TOPIC  1 | Market overview",
        "       2 | Revenue grows 20%",
        "1 of 2 titles are topic-only",
    ]


def _pptx(tmp_path, slide_titles):
    pptx = pytest.importorskip("pptx")
    prs = pptx.Presentation()
    for text in slide_titles:
        slide = prs.slides.add_slide(prs.slide_layouts[5])  # "Title Only"
        if text:
            slide.shapes.title.text = text
    path = tmp_path / "deck.pptx"
    prs.save(path)
    return path


def test_pptx_titles_skip_empty_placeholders(tmp_path):
    path = _pptx(tmp_path, ["Market overview", "", "Revenue grows 20%"])
    assert tt.read_titles(path) == [(1, "Market overview"), (3, "Revenue grows 20%")]


def test_strict_fails_on_a_topic_title(tmp_path, capsys):
    path = _pptx(tmp_path, ["Market overview", "Revenue grows 20%"])
    assert tt.main([str(path), "--strict"]) == 1
    assert tt.main([str(path)]) == 0
    assert "TOPIC  1 | Market overview" in capsys.readouterr().out


def test_strict_passes_when_every_title_is_a_sentence(tmp_path):
    path = _pptx(tmp_path, ["Revenue grows 20%", "Pricing lifts margin"])
    assert tt.main([str(path), "--strict"]) == 0


def test_pdf_deck_end_to_end(tmp_path):
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    path = tmp_path / "deck.pdf"
    c = canvas.Canvas(str(path), pagesize=(960, 540))
    for title in ["Competitive landscape", "Quick commerce wins Tier-1 cities"]:
        c.setFont("Helvetica-Bold", 20)
        c.drawString(40, 500, title)
        c.setFont("Helvetica", 10)
        c.drawString(40, 300, "body text sits lower on the slide")
        c.showPage()
    c.save()
    assert tt.read_titles(path) == [
        (1, "Competitive landscape"), (2, "Quick commerce wins Tier-1 cities"),
    ]
    assert tt.is_topic_only("Competitive landscape")
