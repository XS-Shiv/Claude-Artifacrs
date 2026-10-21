"""Build the skill's web page, site/index.html, from SKILL.md.

The page shows the skill as readable HTML, folds the engine block into a collapsed
section with its line count and sha256, and carries the raw file in a text box with a
copy button. Everything comes from SKILL.md in one pass, so the page cannot drift from
the skill. Edit SKILL.md or page_template.html, then run this script.

Usage:
    python build_page.py            write site/index.html
    python build_page.py --check    exit with status 1 if site/index.html is out of date
"""
from __future__ import annotations

import argparse
import hashlib
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

ENGINE_RE = re.compile(r"<!-- ENGINE START -->\s*`{3}python\n(.*?)\n`{3}\s*<!-- ENGINE END -->", re.S)


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Separate the `key: value` header between the --- lines from the body."""
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}, text
    fields = {}
    for line in match.group(1).splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key.strip()] = value.strip().strip('"')
    return fields, text[match.end():]


def engine_block(code: str) -> str:
    """The engine as a collapsed section: long code stays out of the reading flow."""
    code += "\n"  # the extract step in SKILL.md hashes the code with a trailing newline
    digest = hashlib.sha256(code.encode()).hexdigest()[:12]
    lines = len(code.splitlines())
    return (
        '<details class="engine" id="engine-code">'
        f"<summary>Engine code: {lines} lines, sha256 <code>{digest}</code></summary>"
        f'<pre><code class="language-python">{html.escape(code)}</code></pre></details>'
    )


def render_article(body: str) -> str:
    """Turn the skill's markdown body into the HTML that sits inside <article>."""
    import markdown  # imported here so split_frontmatter works without it installed

    body = re.sub(r"\A\s*# .*\n", "", body, count=1)  # the page header already shows the title
    match = ENGINE_RE.search(body)
    engine = engine_block(match.group(1)) if match else ""
    if match:
        body = body[:match.start()] + "ENGINESLOT" + body[match.end():]
    article = markdown.markdown(body, extensions=["tables", "fenced_code", "toc"])
    article = article.replace("<table>", '<div class="table-wrap"><table>')
    article = article.replace("</table>", "</table></div>")
    return article.replace("<p>ENGINESLOT</p>", engine)


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
