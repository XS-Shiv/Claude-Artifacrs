import re
from pathlib import Path

import pytest

import rubric as rb

ALL_FIVE = ["clarity=5", "feasibility=5", "evidence=5", "story=5", "qa=5"]
MIXED = ["clarity=5", "feasibility=3", "evidence=1", "story=3", "qa=5"]


def test_parse_accepts_every_criterion_once():
    assert rb.parse_scores(MIXED) == {"clarity": 5, "feasibility": 3, "evidence": 1, "story": 3, "qa": 5}


def test_parse_is_forgiving_about_case_and_q_and_a():
    scores = rb.parse_scores(["Clarity=5", "FEASIBILITY=3", "Evidence=1", "Story=3", "Q&A=5"])
    assert scores["qa"] == 5 and scores["clarity"] == 5


@pytest.mark.parametrize("bad, message", [
    (["clarity=4", *ALL_FIVE[1:]], "1, 3 or 5"),
    (["clarity=high", *ALL_FIVE[1:]], "1, 3 or 5"),
    (["polish=5", *ALL_FIVE], "expected one of"),
    (["clarity", *ALL_FIVE[1:]], "expected one of"),
    (ALL_FIVE[:4], "missing scores for: qa"),
    (["clarity=3", *ALL_FIVE], "scored twice"),
])
def test_parse_rejects_bad_input(bad, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        rb.parse_scores(bad)


def test_ranked_puts_weakest_first_and_keeps_rubric_order_on_ties():
    assert rb.ranked(rb.parse_scores(MIXED)) == ["evidence", "feasibility", "story", "clarity", "qa"]


def test_report_lists_weakest_first_with_what_a_five_needs():
    out = rb.report(rb.parse_scores(MIXED))
    lines = out.splitlines()
    assert lines[0] == "RUBRIC  17/25  |  3 of 5 under 5"
    assert lines[2].startswith("1  Evidence") and "Claims only" in lines[2]
    assert "needs: Numbers and sources" in lines[2]
    assert "needs" not in lines[-3]  # Q&A at 5 has nothing to fix
    assert lines[-1] == "Fix first: Evidence"


def test_report_with_all_fives_has_nothing_to_fix():
    out = rb.report(rb.parse_scores(ALL_FIVE))
    assert out.startswith("RUBRIC  25/25  |  0 of 5 under 5")
    assert "needs" not in out and "Fix first" not in out


def test_strict_exit_codes(capsys):
    assert rb.main(ALL_FIVE + ["--strict"]) == 0
    assert rb.main(MIXED + ["--strict"]) == 1
    assert rb.main(MIXED) == 0
    assert "Fix first: Evidence" in capsys.readouterr().out


def test_bad_input_exits_with_usage_error(capsys):
    with pytest.raises(SystemExit) as exc:
        rb.main(["clarity=2"])
    assert exc.value.code == 2
    assert "1, 3 or 5" in capsys.readouterr().err


def test_rubric_matches_the_table_in_skill_md():
    skill = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(encoding="utf-8")
    for label, levels in rb.RUBRIC.values():
        row = f"| {label} | {levels[1]} | {levels[3]} | {levels[5]} |"
        assert row in skill, row
