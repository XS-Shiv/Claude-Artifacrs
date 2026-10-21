import hashlib
import html
import re

import pytest

import build_page as bp

pytest.importorskip("markdown")

SKILL_TEXT = bp.SKILL.read_text(encoding="utf-8")
ENGINE = bp.ENGINE_RE.search(SKILL_TEXT).group(1) + "\n"

SMALL_SKILL = """---
name: "tiny-skill"
description: "Says "hello" & stops."
---

# Tiny skill

Opening line.

## Engine

<!-- ENGINE START -->
```python
print("<hi>")
```
<!-- ENGINE END -->
"""

SMALL_TEMPLATE = (
    '<meta name="description" content="<!-- DESCRIPTION -->">'
    "<article><!-- ARTICLE --></article><textarea><!-- RAW_SKILL --></textarea>"
)


def test_frontmatter_values_lose_their_quotes():
    fields, body = bp.split_frontmatter(SMALL_SKILL)
    assert fields == {"name": "tiny-skill", "description": 'Says "hello" & stops.'}
    assert body.lstrip().startswith("# Tiny skill")


def test_engine_is_folded_into_a_details_block_with_its_hash():
    article = bp.render_article(bp.split_frontmatter(SMALL_SKILL)[1])
    digest = hashlib.sha256(b'print("<hi>")\n').hexdigest()[:12]
    assert "<h1" not in article
    assert '<details class="engine" id="engine-code">' in article
    assert f"1 lines, sha256 <code>{digest}</code>" in article
    assert "print(&quot;&lt;hi&gt;&quot;)" in article
    assert "ENGINESLOT" not in article and "ENGINE START" not in article


def test_page_fills_every_slot_and_escapes_the_raw_skill():
    page = bp.build(SMALL_SKILL, SMALL_TEMPLATE)
    assert "<!--" not in page
    assert 'content="Says &quot;hello&quot; &amp; stops."' in page
    raw = re.search(r"<textarea>(.*)</textarea>", page, re.S).group(1)
    assert html.unescape(raw) == SMALL_SKILL


def test_template_missing_a_slot_is_rejected():
    with pytest.raises(ValueError):
        bp.build(SMALL_SKILL, "<article><!-- ARTICLE --></article>")


def test_engine_on_the_page_is_morph_py_with_the_skills_hash():
    page = bp.build()
    code = re.search(r'id="engine-code">.*?<pre><code[^>]*>(.*?)</code></pre>', page, re.S).group(1)
    assert html.unescape(code) == ENGINE == (bp.HERE / "morph.py").read_text(encoding="utf-8")
    digest = hashlib.sha256(ENGINE.encode()).hexdigest()[:12]
    assert f"sha256 <code>{digest}</code>" in page
    assert f"sha256 `{digest}`" in SKILL_TEXT


def test_every_heading_in_the_skill_is_on_the_page():
    page = bp.build()
    prose = bp.ENGINE_RE.sub("", SKILL_TEXT)
    headings = re.findall(r"^#{2,3} (.+)$", prose, re.M)
    assert len(headings) > 8
    for heading in headings:
        assert f">{html.escape(heading, quote=False)}</h" in page, heading


def test_raw_skill_on_the_page_is_the_skill_file_exactly():
    raw = re.search(r'<textarea id="raw-text"[^>]*>(.*?)</textarea>', bp.build(), re.S).group(1)
    assert html.unescape(raw) == SKILL_TEXT


def test_every_in_page_link_has_a_target():
    page = bp.build()
    ids = set(re.findall(r'\bid="([^"]+)"', page))
    links = set(re.findall(r'href="#([^"]+)"', page))
    assert links and links <= ids, links - ids


def test_committed_page_is_up_to_date_with_the_skill():
    assert bp.PAGE.read_text(encoding="utf-8") == bp.build(), "run: python build_page.py"
    assert bp.main(["--check"]) == 0
