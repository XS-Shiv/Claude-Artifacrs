import json
from pathlib import Path

import pytest

import tier_order as to

EX = Path(__file__).resolve().parent.parent / "examples"


def t(guid, tier, topic):
    return {"guid": guid, "title": guid, "tier": tier, "topic": topic}


def guids(order):
    return [e["guid"] for e in order]


def test_only_s_and_a_are_queued():
    tiers = to.parse_tiers([t("s", "S", "web3"), t("b", "B", "web3"), t("c", "c", "web3"), t("a", "a", "web3")])
    assert guids(to.posting_order(tiers, [])) == ["s", "a"]


def test_topics_alternate_and_s_comes_first_within_a_topic():
    tiers = to.parse_tiers([
        t("d-a1", "A", "design-ai"), t("d-s", "S", "design"), t("d-a2", "A", "ai"),
        t("w-a", "A", "web3"), t("w-s", "S", "Web3"),
    ])
    assert guids(to.posting_order(tiers, [])) == ["d-s", "w-s", "d-a1", "w-a", "d-a2"]


def test_first_run_leads_with_best_earliest_topic():
    tiers = to.parse_tiers([t("d-a", "A", "design-ai"), t("w-s", "S", "web3")])
    assert guids(to.posting_order(tiers, [])) == ["w-s", "d-a"]


def test_starts_with_the_topic_not_posted_last():
    tiers = to.parse_tiers([t("d1", "S", "design-ai"), t("d2", "A", "design-ai"), t("w1", "S", "web3"), t("w2", "A", "web3")])
    posted = [{"guid": "w1"}, {"guid": "d1"}, {"guid": "unlisted"}]
    assert guids(to.posting_order(tiers, posted)) == ["w2", "d2"]


def test_leftover_topic_follows_when_the_other_runs_out():
    tiers = to.parse_tiers([t("w1", "S", "web3"), t("w2", "A", "web3"), t("w3", "A", "web3"), t("d1", "A", "design-ai")])
    assert guids(to.posting_order(tiers, [])) == ["w1", "d1", "w2", "w3"]


def test_everything_posted_gives_empty_order():
    tiers = to.parse_tiers([t("w1", "S", "web3")])
    assert to.posting_order(tiers, [{"guid": "w1"}]) == []


@pytest.mark.parametrize("bad, msg", [
    ({"guid": "x"}, "tier list must be"),
    ([{"title": "no guid"}], "no guid"),
    ([t("x", "Z", "web3")], "tier must be"),
    ([t("x", "S", "crypto")], "topic must be"),
    ([t("x", "S", "web3"), t("x", "A", "web3")], "listed twice"),
])
def test_bad_tier_lists_are_refused(bad, msg):
    with pytest.raises(ValueError, match=msg):
        to.parse_tiers(bad)


def test_cli_example_files(capsys):
    assert to.main([str(EX / "tiers.json"), "--posted", str(EX / "posted.json")]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line[len(" 1. S  design-ai  "):] for line in lines] == [
        "Gas Fees Are a Design Problem", "Empty States Are Onboarding",
        "Wallets Should Feel Like Inboxes", "Prompts Are the New Forms",
    ]


def test_cli_next_json_and_exit_codes(tmp_path, capsys):
    assert to.main([str(EX / "tiers.json"), "--posted", str(EX / "posted.json"), "--next", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["title"] == "Gas Fees Are a Design Problem"
    tiers = tmp_path / "tiers.json"
    tiers.write_text(json.dumps([t("w1", "S", "web3")]))
    posted = tmp_path / "posted.json"
    posted.write_text(json.dumps([{"guid": "w1"}]))
    assert to.main([str(tiers), "--posted", str(posted)]) == 1
    tiers.write_text("{}")
    assert to.main([str(tiers)]) == 2
