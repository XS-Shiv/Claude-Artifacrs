import json

import pytest

import check_thread as ct

LINK = "Full essay: https://medium.com/@sample/a-long-essay-slug-1c2d3e4f5061"
GOOD = [
    "Every tooltip is a small admission that the screen did not explain itself.",
    "The fix is rarely a better tooltip. It is a label that says what the button does.",
    "Start by deleting one tooltip a week and see who notices.",
    LINK,
]


def run(tmp_path, tweets, capsys):
    path = tmp_path / "thread.json"
    path.write_text(json.dumps({"title": "T", "link": "https://m.com", "tweets": tweets}), encoding="utf-8")
    code = ct.main(str(path))
    return code, capsys.readouterr().out


def test_a_clean_thread_passes(tmp_path, capsys):
    code, out = run(tmp_path, GOOD, capsys)
    assert code == 0
    assert "FAIL" not in out and out.count("PASS") == 5


def test_links_count_as_23_and_wide_characters_as_2():
    assert ct.x_length("see https://example.com/" + "x" * 200) == len("see ") + 23
    assert ct.x_length("世界") == 4
    assert ct.x_length("a—b") == 3  # em dash sits in the light punctuation range


@pytest.mark.parametrize("tweets, fails", [
    (GOOD[:2], "3 to 5 tweets"),
    (GOOD[:3] + ["a" * 281, LINK], "tweet 4 is 281"),
    (["see https://x.com/a"] + GOOD[1:], "link in tweet 1"),
    (GOOD[:3] + ["no link here"], "exactly one link"),
    (["Ship it #buildinpublic"] + GOOD[1:], "hashtag in tweet 1"),
    (["Ship it \U0001F680"] + GOOD[1:], "emoji in tweet 1"),
    (["1/ Ship it"] + GOOD[1:], "numbering in tweet 1"),
    (["Ship it (2/4)"] + GOOD[1:], "numbering in tweet 1"),
    (["Ship it — now"] + GOOD[1:], "em dash in tweet 1"),
    ([GOOD[0], GOOD[0].upper(), GOOD[2], LINK], "tweet 2 repeats"),
    ([GOOD[0], "   ", GOOD[2], LINK], "tweet 2 is empty"),
])
def test_each_rule_fails_on_its_own(tmp_path, capsys, tweets, fails):
    code, out = run(tmp_path, tweets, capsys)
    assert code == 1
    assert fails in out


def test_a_hash_inside_a_word_is_not_a_hashtag(tmp_path, capsys):
    code, out = run(tmp_path, ["We use C# daily and issue#4 is closed"] + GOOD[1:], capsys)
    assert code == 0, out


@pytest.mark.parametrize("content", ["not json", json.dumps({"title": "no tweets"}), json.dumps({"tweets": "one"})])
def test_a_bad_file_exits_2(tmp_path, capsys, content):
    path = tmp_path / "thread.json"
    path.write_text(content, encoding="utf-8")
    assert ct.main(str(path)) == 2
    assert "not a thread.json" in capsys.readouterr().out
