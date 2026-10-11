"""Build the skill's web page, site/index.html, from SKILL.md.

The page shows the skill as readable HTML and also carries the raw file in a text box
with a copy button. Both come from SKILL.md in one pass, so the page cannot drift from
the skill. Edit SKILL.md or page_template.html, then run this script.

Usage:
    python build_page.py            write site/index.html
    python build_page.py --check    exit with status 1 if site/index.html is out of date
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from typing import Sequence

HERE = Path(__file__).parent
SKILL = HERE / "SKILL.md"
TEMPLATE = HERE / "page_template.html"
PAGE = HERE / "site" / "index.html"

ARTICLE_SLOT = "<!-- ARTICLE -->"
RAW_SLOT = "<!-- RAW_SKILL -->"
DESCRIPTION_SLOT = "<!-- DESCRIPTION -->"


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Separate the `key: value` header between the --- lines from the body."""
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}, text
    fields = dict(line.split(": ", 1) for line in match.group(1).splitlines() if ": " in line)
    return fields, text[match.end():]


def render_article(body: str) -> str:
    """Turn the skill's markdown body into the HTML that sits inside <article>."""
    import markdown  # imported here so split_frontmatter works without it installed

    body = re.sub(r"\A\s*# .*\n", "", body, count=1)  # the page header already shows the title
    article = markdown.markdown(body, extensions=["tables", "fenced_code", "toc"])
    # wide tables scroll inside their own box instead of stretching the page
    article = article.replace("<table>", '<div class="table-wrap"><table>')
    article = article.replace("</table>", "</table></div>")
    # code blocks with no language are the deck cards, which wrap like prose
    return article.replace("<pre><code>", '<pre class="card"><code>')


def build(skill_text: str | None = None, template: str | None = None) -> str:
    """Return the full page for the given skill text and template."""
    skill_text = SKILL.read_text(encoding="utf-8") if skill_text is None else skill_text
    template = TEMPLATE.read_text(encoding="utf-8") if template is None else template
    for slot in (ARTICLE_SLOT, RAW_SLOT, DESCRIPTION_SLOT):
        if template.count(slot) != 1:
            raise ValueError(f"the template must contain {slot} exactly once")
    fields, body = split_frontmatter(skill_text)
    page = template.replace(DESCRIPTION_SLOT, html.escape(fields.get("description", "")))
    page = page.replace(ARTICLE_SLOT, render_article(body))
    return page.replace(RAW_SLOT, html.escape(skill_text))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build site/index.html from SKILL.md.")
    parser.add_argument("--check", action="store_true",
                        help="do not write; exit with status 1 if the page is out of date")
    args = parser.parse_args(argv)
    page = build()
    if args.check:
        if PAGE.is_file() and PAGE.read_text(encoding="utf-8") == page:
            return 0
        print("site/index.html is out of date; run: python build_page.py")
        return 1
    PAGE.parent.mkdir(exist_ok=True)
    PAGE.write_text(page, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
