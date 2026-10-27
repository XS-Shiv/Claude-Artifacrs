from pathlib import Path

import pytest

import next_essay as ne

EX = Path(__file__).resolve().parent.parent / "examples"
FEED = (EX / "feed_three.xml").read_text(encoding="utf-8")
TOOLTIPS = "https://medium.com/p/a012d600d0c5"
GAS = "https://medium.com/p/1c2d3e4f5061"
EMPTY = "https://medium.com/p/0b1c2d3e4f50"


def feed(*items: str) -> str:
    return "<rss><channel>" + "".join(items) + "</channel></rss>"


def item(guid: str, date: str | None = None) -> str:
    when = f"<pubDate>{date}</pubDate>" if date else ""
    return f"<item><title>{guid}</title><link>https://m.com/{guid}</link><guid>{guid}</guid>{when}</item>"


def test_newest_first_regardless_of_feed_order():
    assert [i["guid"] for i in ne.unposted(FEED, set())] == [TOOLTIPS, GAS, EMPTY]


def test_posted_essays_are_skipped():
    assert ne.next_essay(FEED, {TOOLTIPS})["guid"] == GAS
    assert ne.next_essay(FEED, {TOOLTIPS, GAS})["guid"] == EMPTY


def test_none_when_everything_is_posted():
    assert ne.next_essay(FEED, {TOOLTIPS, GAS, EMPTY}) is None


def test_time_zones_are_compared_as_instants():
    xml = feed(item("a", "Sat, 24 Oct 2026 10:00:00 +0530"), item("b", "Sat, 24 Oct 2026 05:00:00 GMT"))
    assert ne.next_essay(xml, set())["guid"] == "b"  # 05:00 GMT is after 04:30 GMT


def test_undated_items_sort_last_and_ties_keep_feed_order():
    xml = feed(item("x"), item("y", "garbage"), item("z", "Sun, 25 Oct 2026 14:00:00 GMT"))
    assert [i["guid"] for i in ne.unposted(xml, set())] == ["z", "x", "y"]


def test_posted_log_accepts_strings_and_objects():
    assert ne.posted_guids([" a ", {"guid": "b", "title": "B"}]) == {"a", "b"}


@pytest.mark.parametrize("bad", [{"guid": "a"}, [{"title": "no guid"}], [""], [3]])
def test_malformed_posted_log_is_refused(bad):
    with pytest.raises(ValueError):
        ne.posted_guids(bad)


def test_cli_picks_from_example_log(capsys):
    assert ne.main([str(EX / "feed_three.xml"), "--posted", str(EX / "posted.json")]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "Gas Fees Are a Design Problem",
        "https://medium.com/@sample/gas-fees-are-a-design-problem-1c2d3e4f5061",
        "2026-10-24",
    ]


def test_cli_missing_log_means_nothing_posted(tmp_path, capsys):
    assert ne.main([str(EX / "feed_three.xml"), "--posted", str(tmp_path / "none.json"), "--json"]) == 0
    assert '"guid": "' + TOOLTIPS in capsys.readouterr().out


def test_cli_exit_codes(tmp_path):
    log = tmp_path / "posted.json"
    log.write_text(f'["{TOOLTIPS}", "{GAS}", "{EMPTY}"]', encoding="utf-8")
    assert ne.main([str(EX / "feed_three.xml"), "--posted", str(log)]) == 1
    log.write_text('{"not": "a list"}', encoding="utf-8")
    assert ne.main([str(EX / "feed_three.xml"), "--posted", str(log)]) == 2
