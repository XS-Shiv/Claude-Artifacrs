import pytest

import x_length as xl


def test_latin_text_counts_one_per_character():
    assert xl.x_length("hello, world") == 12
    assert xl.x_length("café — “quoted”") == 15  # accents, em dash and curly quotes are 1


def test_cjk_and_ellipsis_count_two():
    assert xl.x_length("日本語") == 6
    assert xl.x_length("한국") == 4
    assert xl.x_length("wait…") == 6


def test_a_link_counts_23_however_long():
    assert xl.x_length("https://a.co") == 23
    assert xl.x_length("read https://medium.com/" + "x" * 100 + " now") == 5 + 23 + 4


@pytest.mark.parametrize(
    "emoji",
    [
        "\U0001F600",                                   # grinning face
        "\U0001F44D\U0001F3FD",                         # thumbs up, skin tone
        "\U0001F468‍\U0001F469‍\U0001F467",   # family (ZWJ)
        "\U0001F1EE\U0001F1F3",                         # flag: India
        "❤️",                                 # red heart
        "1️⃣",                                # keycap 1
    ],
)
def test_one_emoji_counts_two_whatever_its_code_points(emoji):
    assert xl.x_length(emoji) == 2
    assert xl.x_length(f"a{emoji}b") == 4


def test_two_flags_are_two_emoji():
    assert xl.x_length("\U0001F1EE\U0001F1F3\U0001F1EF\U0001F1F5") == 4


def test_text_is_nfc_normalised():
    assert xl.x_length("é") == 1  # e + combining acute -> é


def test_segments_never_split_a_link_or_an_emoji():
    pieces = [p for p, _ in xl.segments("hi https://x.co/ab \U0001F44D\U0001F3FD")]
    assert pieces == ["h", "i", " ", "https://x.co/ab", " ", "\U0001F44D\U0001F3FD"]


def test_fits_uses_the_280_limit():
    assert xl.fits("x" * 280)
    assert not xl.fits("x" * 279 + "…")
    assert not xl.fits("日" * 141)


def test_cli_reports_length_and_exit_status(capsys):
    assert xl.main(["日本", "ok"]) == 0
    assert capsys.readouterr().out.strip() == "7/280"
    assert xl.main(["日" * 141]) == 1
    assert "over by 2" in capsys.readouterr().out
    assert xl.main([]) == 2
