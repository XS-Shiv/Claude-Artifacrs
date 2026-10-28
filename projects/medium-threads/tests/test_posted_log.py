import json
from datetime import datetime, timedelta, timezone

import pytest

import next_essay
import posted_log as pl

IST = timezone(timedelta(hours=5, minutes=30))
GAS = "https://medium.com/p/1c2d3e4f5061"


def gas(**over):
    args = dict(guid=GAS, title="Gas Fees Are a Design Problem",
                link="https://medium.com/@sample/gas-fees-1c2d3e4f5061", tweet_id="1850000000000000001")
    args.update(over)
    return pl.record(**args, now=datetime(2026, 10, 28, 21, 0, 30, 999, tzinfo=IST))


def test_record_has_all_fields_and_utc_time():
    r = gas(title="  Gas Fees Are a Design Problem ")
    assert r == {
        "guid": GAS,
        "title": "Gas Fees Are a Design Problem",
        "link": "https://medium.com/@sample/gas-fees-1c2d3e4f5061",
        "tweet_id": "1850000000000000001",
        "posted_at": "2026-10-28T15:30:30+00:00",
    }


@pytest.mark.parametrize("over, msg", [
    (dict(title=" "), "missing title"),
    (dict(link=""), "missing link"),
    (dict(tweet_id="abc"), "digits"),
])
def test_record_rejects_bad_input(over, msg):
    with pytest.raises(ValueError, match=msg):
        gas(**over)


def test_missing_file_is_empty_log(tmp_path):
    assert pl.load(tmp_path / "none.json") == []


def test_add_writes_a_list_next_essay_can_read(tmp_path):
    log = tmp_path / "state" / "posted.json"
    pl.add(log, gas())
    data = json.loads(log.read_text(encoding="utf-8"))
    assert data[0]["tweet_id"] == "1850000000000000001"
    assert next_essay.load_posted(log) == {GAS}
    assert [p.name for p in log.parent.iterdir()] == ["posted.json"]  # no temp left behind


def test_same_guid_is_refused_and_log_unchanged(tmp_path):
    log = tmp_path / "posted.json"
    pl.add(log, gas())
    before = log.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="already posted"):
        pl.add(log, gas(tweet_id="1850000000000000002"))
    assert log.read_text(encoding="utf-8") == before


def test_legacy_string_entries_become_records(tmp_path):
    log = tmp_path / "posted.json"
    log.write_text('["https://medium.com/p/old"]', encoding="utf-8")
    records = pl.add(log, gas())
    assert records[0] == {"guid": "https://medium.com/p/old"}
    assert json.loads(log.read_text(encoding="utf-8"))[0] == {"guid": "https://medium.com/p/old"}


def test_malformed_log_is_an_error(tmp_path):
    log = tmp_path / "posted.json"
    log.write_text('{"guid": "x"}', encoding="utf-8")
    with pytest.raises(ValueError, match="JSON list"):
        pl.load(log)
    log.write_text('[{"title": "no guid"}]', encoding="utf-8")
    with pytest.raises(ValueError, match="no guid"):
        pl.load(log)


def test_failed_write_keeps_old_log(tmp_path, monkeypatch):
    log = tmp_path / "posted.json"
    pl.add(log, gas())
    before = log.read_text(encoding="utf-8")

    def boom(*_):
        raise OSError("disk full")
    monkeypatch.setattr(pl.os, "replace", boom)
    with pytest.raises(OSError):
        pl.add(log, gas(guid="https://medium.com/p/new"))
    assert log.read_text(encoding="utf-8") == before
    assert [p.name for p in tmp_path.iterdir()] == ["posted.json"]


def test_cli_add_then_duplicate_then_list(tmp_path, capsys):
    log = str(tmp_path / "posted.json")
    argv = ["add", log, "--guid", GAS, "--title", "Gas Fees", "--link", "https://m.com/g", "--tweet-id", "42"]
    assert pl.main(argv) == 0
    assert "1 posted" in capsys.readouterr().out
    assert pl.main(argv) == 1
    assert "already posted" in capsys.readouterr().err
    assert pl.main(["add", log, "--guid", "g2", "--title", "T", "--link", "L", "--tweet-id", "x"]) == 2
    assert pl.main(["list", log]) == 0
    assert "Gas Fees" in capsys.readouterr().out
