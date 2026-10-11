import shutil

import pytest

import deck_reader as dr
from deck_reader import SlideStats


def test_type_size_is_unchanged_on_a_standard_slide():
    assert dr.scale_to_slide(12, 960) == 12


def test_type_size_is_scaled_up_from_a_narrower_page():
    # 9pt on a 10in-wide export is 12pt on a 13.33in-wide slide
    assert dr.scale_to_slide(9, 720) == pytest.approx(12)


def test_zero_page_width_is_rejected():
    with pytest.raises(ValueError):
        dr.scale_to_slide(12, 0)


def test_slide_stats_reports_count_median_and_smallest():
    stats = dr.slide_stats(3, [10, 10, 20, 8, 10], page_width_pt=960, images=2)
    assert stats == SlideStats(number=3, words=5, images=2, body_pt=10, smallest_pt=8)


def test_slide_with_no_text_reports_zeros_and_keeps_its_images():
    assert dr.slide_stats(1, [], page_width_pt=960, images=4) == SlideStats(1, 0, 4, 0.0, 0.0)


def test_content_slides_drops_covers_and_dividers():
    deck = [SlideStats(1, 5, 1, 30, 30), SlideStats(2, 60, 0, 11, 8), SlideStats(3, 300, 2, 10, 8)]
    assert [s.number for s in dr.content_slides(deck)] == [2, 3]


def test_median_words_uses_content_slides_only():
    deck = [SlideStats(1, 5, 0, 30, 30), SlideStats(2, 200, 0, 11, 8), SlideStats(3, 400, 0, 10, 8)]
    assert dr.median_words(deck) == 300


def test_deck_with_no_content_slides_has_no_median():
    # the one-file script this grew out of crashed on a deck like this
    cover_only = [SlideStats(1, 5, 0, 30, 30)]
    assert dr.median_words(cover_only) is None
    assert dr.format_report(cover_only).splitlines()[0] == "1 slide, 0 content slides"


def test_report_has_a_summary_line_and_one_line_per_slide():
    deck = [SlideStats(1, 4, 1, 40.0, 40.0), SlideStats(2, 310, 3, 11.0, 8.0)]
    assert dr.format_report(deck) == (
        "2 slides, 1 content slide, median 310 words per content slide\n"
        " 1 |    4 words |  1 images | body 40.0pt | smallest 40.0pt\n"
        " 2 |  310 words |  3 images | body 11.0pt | smallest  8.0pt"
    )


def test_readable_slide_within_the_word_limit_has_no_flags():
    assert dr.slide_flags(SlideStats(2, 450, 0, 11.0, 8.0)) == []


def test_small_type_is_flagged():
    assert dr.slide_flags(SlideStats(2, 300, 0, 11.0, 6.7)) == [
        "type at 6.7pt, under the 8pt floor"
    ]


def test_type_that_prints_as_the_floor_is_not_flagged():
    # 7.96pt shows as 8.0pt in the report, so it must not be reported as under 8pt
    assert dr.slide_flags(SlideStats(2, 300, 0, 11.0, 7.96)) == []


def test_too_many_words_is_flagged():
    assert dr.slide_flags(SlideStats(4, 451, 0, 9.0, 9.0)) == ["451 words, over the 450-word limit"]


def test_slide_with_no_text_is_not_flagged_for_type_size():
    assert dr.slide_flags(SlideStats(1, 0, 3, 0.0, 0.0)) == []


def test_limits_can_be_changed():
    live_deck_slide = SlideStats(3, 130, 0, 14.0, 11.0)
    assert dr.slide_flags(live_deck_slide, min_type_pt=12, max_words=120) == [
        "type at 11.0pt, under the 12pt floor",
        "130 words, over the 120-word limit",
    ]


def test_flags_are_listed_by_slide_under_a_heading():
    deck = [SlideStats(1, 4, 0, 40.0, 40.0), SlideStats(2, 560, 0, 9.0, 5.0)]
    assert dr.format_flags(deck) == (
        "Over the limits:\n"
        "  slide 2: type at 5.0pt, under the 8pt floor\n"
        "  slide 2: 560 words, over the 450-word limit"
    )


def test_deck_within_the_limits_has_nothing_to_list():
    assert dr.format_flags([SlideStats(1, 300, 0, 11.0, 8.0)]) == ""


def build_deck(tmp_path, name="deck.pdf", source_pt=6):
    """A two-slide deck on a 10in-wide page: a cover, then a dense content slide."""
    canvas = pytest.importorskip("reportlab.pdfgen.canvas")
    image = pytest.importorskip("PIL.Image")
    pytest.importorskip("pdfplumber")

    logo = tmp_path / "logo.png"
    image.new("RGB", (8, 8), "navy").save(logo)

    path = tmp_path / name
    c = canvas.Canvas(str(path), pagesize=(720, 405))
    c.setFont("Helvetica-Bold", 30)
    c.drawString(60, 200, "Sample strategy deck")
    c.showPage()

    c.setFont("Helvetica-Bold", 15)
    c.drawString(40, 360, "Sales cost is the largest line")  # 6 words
    c.setFont("Helvetica", 9)
    for row in range(8):  # 8 rows of 10 words
        c.drawString(40, 320 - row * 14, " ".join(f"word{row}{i}" for i in range(10)))
    c.setFont("Helvetica", source_pt)
    c.drawString(40, 20, "Source: assumption")  # 2 words
    c.drawImage(str(logo), 640, 350, width=40, height=40)
    c.showPage()
    c.save()
    return path


@pytest.fixture
def sample_deck(tmp_path):
    return build_deck(tmp_path)


@pytest.fixture
def small_type_deck(tmp_path):
    return build_deck(tmp_path, name="small_type.pdf", source_pt=5)


def test_read_pdf_measures_each_slide(sample_deck):
    cover, content = dr.read_pdf(sample_deck)

    assert (cover.number, cover.words, cover.images) == (1, 3, 0)
    assert cover.body_pt == pytest.approx(40)  # 30pt on a 720pt-wide page

    assert (content.number, content.words, content.images) == (2, 88, 1)
    assert content.body_pt == pytest.approx(12)  # the 9pt body text
    assert content.smallest_pt == pytest.approx(8)  # the 6pt source line


def test_cli_prints_the_report(sample_deck, capsys):
    assert dr.main([str(sample_deck)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "2 slides, 1 content slide, median 88 words per content slide"
    assert len(out) == 3


@pytest.mark.skipif(shutil.which("pdftoppm") is None, reason="poppler is not installed")
def test_cli_renders_one_image_per_slide(sample_deck, tmp_path, capsys):
    out_dir = tmp_path / "slides"
    assert dr.main([str(sample_deck), str(out_dir)]) == 0
    assert len(list(out_dir.glob("s-*.jpg"))) == 2


def test_cli_lists_slides_over_the_limits(small_type_deck, capsys):
    assert dr.main([str(small_type_deck)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-2:] == ["Over the limits:", "  slide 2: type at 6.7pt, under the 8pt floor"]


def test_strict_mode_fails_a_deck_over_the_limits(small_type_deck, sample_deck, capsys):
    assert dr.main([str(small_type_deck), "--strict"]) == 1
    assert dr.main([str(sample_deck), "--strict"]) == 0


def test_cli_limits_can_be_tightened(sample_deck, capsys):
    assert dr.main([str(sample_deck), "--strict", "--max-words", "80"]) == 1
    assert capsys.readouterr().out.splitlines()[-1] == "  slide 2: 88 words, over the 80-word limit"


def test_cli_rejects_a_missing_file(tmp_path, capsys):
    with pytest.raises(SystemExit) as exit_info:
        dr.main([str(tmp_path / "missing.pdf")])
    assert exit_info.value.code == 2
