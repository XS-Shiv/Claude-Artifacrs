import shutil
from pathlib import Path

import pytest

import deck_card as dc
from deck_reader import SlideStats

needs_poppler = pytest.mark.skipif(shutil.which("pdftoppm") is None, reason="needs poppler")
needs_soffice = pytest.mark.skipif(
    shutil.which("soffice") is None and shutil.which("libreoffice") is None,
    reason="needs LibreOffice",
)


def _pdf(path, titles):
    canvas = pytest.importorskip("reportlab.pdfgen.canvas")
    c = canvas.Canvas(str(path), pagesize=(960, 540))
    for title in titles:
        c.setFont("Helvetica", 32)
        c.drawString(40, 480, title)
        c.showPage()
    c.save()
    return path


def _pptx(path, titles):
    pptx = pytest.importorskip("pptx")
    prs = pptx.Presentation()
    for title in titles:
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = title
    prs.save(str(path))
    return path


def test_slide_images_are_in_slide_order_even_when_padded(tmp_path):
    for name in ["s-10.jpg", "s-02.jpg", "s-01.jpg", "notes.txt"]:
        (tmp_path / name).write_bytes(b"")
    assert [p.name for p in dc.slide_images(tmp_path)] == ["s-01.jpg", "s-02.jpg", "s-10.jpg"]


def test_card_points_the_prompts_at_the_rendered_folder(tmp_path):
    images = [tmp_path / "s-1.jpg"]
    card = dc.build_card("Tiny", [SlideStats(1, 5, 0, 30.0, 30.0)], [(1, "Revenue grows 20%")],
                         images=images)
    assert f"Layout: (fill in from the slide images in {tmp_path}/)" in card
    assert dc.FILL_IN not in card


def test_missing_libreoffice_is_reported(tmp_path, monkeypatch, capsys):
    deck = tmp_path / "deck.pptx"
    deck.write_bytes(b"not a deck")
    monkeypatch.setattr(dc.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="LibreOffice was not found"):
        dc.pptx_to_pdf(deck, tmp_path)


def test_cli_exits_2_when_rendering_fails(tmp_path, monkeypatch, capsys):
    deck = _pdf(tmp_path / "deck.pdf", ["Revenue grows 20%"])

    def fail(*_):
        raise RuntimeError("pdftoppm was not found")

    monkeypatch.setattr(dc.dr, "render_slides", fail)
    assert dc.main([str(deck), "--render", str(tmp_path / "out")]) == 2
    assert "could not render slides: pdftoppm was not found" in capsys.readouterr().err


@needs_poppler
def test_renders_a_pdf_beside_the_card(tmp_path, capsys):
    deck = _pdf(tmp_path / "deck.pdf", ["Market entry plan", "Revenue grows 20%"])
    out = tmp_path / "slides"
    assert dc.main([str(deck), "--render", str(out)]) == 0
    captured = capsys.readouterr()
    assert [p.name for p in dc.slide_images(out)] == ["s-1.jpg", "s-2.jpg"]
    assert f"slide images in {out}/" in captured.out
    assert "Saved 2 slide images" in captured.err


@needs_poppler
@needs_soffice
def test_renders_a_pptx_through_libreoffice(tmp_path):
    deck = _pptx(tmp_path / "deck.pptx", ["Market entry plan", "Revenue grows 20%", "Thank you"])
    images = dc.render(deck, tmp_path / "slides")
    assert [_.name for _ in images] == ["s-1.jpg", "s-2.jpg", "s-3.jpg"]
    assert all(p.stat().st_size > 0 for p in images)
    assert not list(tmp_path.glob("slides/*.pdf"))
