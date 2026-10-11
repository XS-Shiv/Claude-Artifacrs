import html
import re

import pytest

import build_page as bp

pytest.importorskip("markdown")

SKILL_TEXT = bp.SKILL.read_text(encoding="utf-8")

SMALL_SKILL = """---
name: tiny-skill
description: Says "hello" & stops.
---

# Tiny skill

Opening line.

## First part

| Test | Asks |
|---|---|
| Clarity | Can I follow it? |

```python
print("hi")
```

```
Deck: sample card
```
"""

SMALL_TEMPLATE = (
    '<meta name="description" content="<!-- DESCRIPTION -->">'
    "<article><!-- ARTICLE --></article><textarea><!-- RAW_SKILL --></textarea>"
)


def test_frontmatter_is_split_from_the_body():
    fields, body = bp.split_frontmatter(SMALL_SKILL)
    assert fields == {"name": "tiny-skill", "description": 'Says "hello" & stops.'}
    assert body.lstrip().startswith("# Tiny skill")


def test_text_without_frontmatter_is_all_body():
    assert bp.split_frontmatter("# Just a title\n") == ({}, "# Just a title\n")


def test_article_drops_the_title_and_keeps_the_rest():
    article = bp.render_article(bp.split_frontmatter(SMALL_SKILL)[1])
    assert "<h1" not in article
    assert article.startswith("<p>Opening line.</p>")
    assert '<h2 id="first-part">First part</h2>' in article


def test_tables_are_wrapped_so_they_can_scroll():
    article = bp.render_article(bp.split_frontmatter(SMALL_SKILL)[1])
    assert '<div class="table-wrap"><table>' in article
    assert "</table></div>" in article


def test_python_blocks_keep_their_language_and_plain_blocks_become_cards():
    article = bp.render_article(bp.split_frontmatter(SMALL_SKILL)[1])
    assert '<pre><code class="language-python">' in article
    assert '<pre class="card"><code>Deck: sample card' in article


def test_page_fills_every_slot_and_escapes_the_raw_skill():
    page = bp.build(SMALL_SKILL, SMALL_TEMPLATE)
    assert "<!--" not in page
    assert 'content="Says &quot;hello&quot; &amp; stops."' in page
    raw = re.search(r"<textarea>(.*)</textarea>", page, re.S).group(1)
    assert html.unescape(raw) == SMALL_SKILL


def test_template_missing_a_slot_is_rejected():
    with pytest.raises(ValueError):
        bp.build(SMALL_SKILL, "<article><!-- ARTICLE --></article>")


def test_every_heading_in_the_skill_is_on_the_page():
    page = bp.build()
    headings = re.findall(r"^#{2,3} (.+)$", SKILL_TEXT, re.M)
    assert len(headings) > 10
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
