import json

import pytest

import thread as th
from x_length import x_length

TITLE = "Are Tooltips UX or Confessions?"
LINK = "https://medium.com/coinmonks/are-tooltips-ux-or-confessions-a012d600d0c5"


def test_short_text_is_left_alone():
    assert th.cap("short tweet") == "short tweet"
    assert th.cap("x" * 280) == "x" * 280


def test_long_text_is_cut_at_a_word_boundary():
    text = "word " * 80  # 400 chars
    out = th.cap(text.strip())
    assert len(out) <= 280
    assert out.endswith("word…")


def test_cut_goes_mid_word_when_the_last_space_is_too_early():
    text = "a " + "x" * 400
    out = th.cap(text)
    assert x_length(out) == 280  # the ellipsis counts as 2 on X
    assert out == "a " + "x" * 276 + "…"


def test_links_and_spaces_are_removed():
    assert th.clean("  read this https://x.co/abc now  ") == "read this  now"
    assert th.clean(None) == ""
    assert th.clean(42) == "42"


def test_thread_drops_empty_tweets_and_ends_with_the_link():
    thread = th.build_thread(["one", "", None, "two https://a.b/c", "three"], TITLE, LINK)
    assert thread == ["one", "two", "three", f"Full essay: {TITLE}\n{LINK}"]


def test_thread_keeps_at_most_six_drafted_tweets():
    thread = th.build_thread([f"tweet {n}" for n in range(1, 10)], TITLE, LINK)
    assert len(thread) == 7
    assert thread[5] == "tweet 6"


def test_every_tweet_fits_in_280_characters():
    thread = th.build_thread(["y " * 200] * 4, "T" * 300, LINK)
    assert all(x_length(t) <= 280 for t in thread[:-1])
    assert thread[-1].startswith("Full essay: " + "T" * 198 + "…\n")


def test_cap_counts_wide_characters_and_emoji_the_way_x_does():
    out = th.cap("日本 " * 100)  # 300 code points, 500 on X
    assert x_length(out) <= 280 and len(out) < 280
    assert out.endswith("日本…")
    family = "\U0001F468\u200D\U0001F469\u200D\U0001F467"
    out = th.cap("ok " + family * 200)
    assert x_length(out) <= 280
    assert out[:-1].endswith(family)  # an emoji is never split


def test_preview_counts_the_link_as_23():
    preview = th.format_thread([f"Full essay: T\n{LINK}"])
    assert preview.startswith(f"[1/1] {14 + 23} chars")


def test_too_few_usable_tweets_is_refused():
    with pytest.raises(th.ThreadError, match="only 2 usable tweets"):
        th.build_thread(["one", "https://only.a/link", "two"], TITLE, LINK)


def test_preview_numbers_each_tweet():
    preview = th.format_thread(["ab", "cde"])
    assert preview == "[1/2] 2 chars\nab\n\n[2/2] 3 chars\ncde"


def test_cli_prints_the_example_thread(capsys):
    assert th.main(["examples/draft.json", "--json"]) == 0
    thread = json.loads(capsys.readouterr().out)
    assert len(thread) == 5
    assert "example.com" not in thread[2]
    assert thread[-1] == f"Full essay: {TITLE}\n{LINK}"


def test_cli_exits_1_on_a_thin_draft(tmp_path, capsys):
    draft = tmp_path / "thin.json"
    draft.write_text(json.dumps({"title": TITLE, "link": LINK, "tweets": ["only one"]}))
    assert th.main([str(draft)]) == 1
    assert "nothing would be posted" in capsys.readouterr().err


def test_cli_exits_2_on_a_file_that_is_not_a_draft(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"tweets": ["a", "b", "c"]}')
    assert th.main([str(bad)]) == 2
    assert "is not a draft" in capsys.readouterr().err
