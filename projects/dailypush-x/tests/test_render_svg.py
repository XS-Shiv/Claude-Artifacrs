import shutil
import struct
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "render_svg.js"
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900">'
       '<rect width="1600" height="900" fill="#F5F1EA"/><circle cx="800" cy="450" r="200" fill="#E8735A"/></svg>')

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def render(tmp_path, svg, *size):
    src = tmp_path / "hook.svg"
    src.write_text(svg, encoding="utf-8")
    out = tmp_path / "images" / "hook.png"
    proc = subprocess.run(["node", str(SCRIPT), str(src), str(out), *size],
                          capture_output=True, text=True, timeout=120)
    return proc, out


def png_size(path):
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", head[16:24])


def test_renders_a_1600x900_png_into_a_new_folder(tmp_path):
    proc, out = render(tmp_path, SVG)
    if proc.returncode and "Cannot find module 'playwright'" in proc.stderr:
        pytest.skip("playwright is not installed for node")
    assert proc.returncode == 0, proc.stderr
    assert png_size(out) == (1600, 900)


def test_custom_size(tmp_path):
    proc, out = render(tmp_path, SVG, "800", "450")
    if proc.returncode and "Cannot find module 'playwright'" in proc.stderr:
        pytest.skip("playwright is not installed for node")
    assert proc.returncode == 0, proc.stderr
    assert png_size(out) == (800, 450)


def test_text_in_the_image_is_refused(tmp_path):
    proc, out = render(tmp_path, SVG.replace("</svg>", "<text x='10' y='10'>hi</text></svg>"))
    assert proc.returncode == 1 and "<text>" in proc.stderr
    assert not out.exists()


def test_a_file_that_is_not_svg_exits_2(tmp_path):
    proc, out = render(tmp_path, "<html>nope</html>")
    assert proc.returncode == 2 and "not an SVG" in proc.stderr
