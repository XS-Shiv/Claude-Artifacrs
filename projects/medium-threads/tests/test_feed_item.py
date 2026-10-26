from pathlib import Path

import pytest

import feed_item as fi

FEED = Path(__file__).resolve().parent.parent / "examples" / "feed.xml"
LINK = "https://medium.com/coinmonks/are-tooltips-ux-or-confessions-a012d600d0c5"


def test_paragraphs_are_split_and_entities_decoded():
    out = fi.html_to_text("<p>It&#8217;s A &amp; B</p><p>two&nbsp;words</p>")
    assert out == "It’s A & B\n\ntwo words"


def test_entities_are_decoded_only_once():
    assert fi.html_to_text("<p>&amp;lt;tag&amp;gt;</p>") == "&lt;tag&gt;"


def test_figures_scripts_and_styles_are_dropped():
    markup = "<figure><img src='x'><figcaption>cap</figcaption></figure><script>x()</script><p>kept</p>"
    assert fi.html_to_text(markup) == "kept"


def test_footer_is_dropped_only_when_last():
    footer = "<p><a>T</a> was originally published in <a>Pub</a> on Medium.</p>"
    assert fi.html_to_text("<p>body</p>" + footer) == "body"
    middle = "<p>It was originally published in 1999.</p><p>end</p>"
    assert fi.html_to_text(middle).startswith("It was originally")


def test_tracking_query_and_fragment_are_removed():
    assert fi.clean_link(" " + LINK + "?source=rss----721b---4#x ") == LINK


def test_example_feed_item():
    [item] = fi.read_feed(FEED.read_text(encoding="utf-8"))
    assert item["title"] == "Are Tooltips UX or Confessions?"
    assert item["link"] == LINK
    assert item["guid"] == "https://medium.com/p/a012d600d0c5"
    assert item["text"].startswith("Every tooltip is a small admission")
    assert "originally published" not in item["text"]
    assert "Labels that need help\n\nIcons nobody reads" in item["text"]


def test_item_without_link_is_refused():
    xml = "<rss><channel><item><title>T</title></item></channel></rss>"
    with pytest.raises(ValueError):
        fi.read_feed(xml)


def test_cli_json_and_bad_index(capsys):
    assert fi.main([str(FEED), "--json"]) == 0
    assert '"link": "' + LINK in capsys.readouterr().out
    assert fi.main([str(FEED), "--index", "5"]) == 2
