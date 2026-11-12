"""Checks for taking a published event down again (`python -m harness unpublish`)."""
import json
from datetime import datetime
from pathlib import Path

import pytest

import harness.__main__ as cli
from harness.config import OSLO, load_config
from harness.pipeline import run
from harness.publish import (
    UNPUBLISHED,
    approve,
    load_blocked,
    published_events,
    unpublish,
)
from web.app import create_app

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "testing" / "kulturnett_SYNTHETIC_2026-11-02.json"
NOW = datetime(2026, 11, 2, 8, 0, tzinfo=OSLO)
QUIET = {"log": lambda *_: None}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _run(base: Path, offline_file: Path = FIXTURE) -> Path:
    report = run(load_config(), NOW, offline_file=offline_file, classifier="baseline", base=base, **QUIET)
    return base / "staging" / report["run_id"]


def _published(base: Path) -> list[dict]:
    """Run the fixture and approve it; return the published events."""
    approve(_run(base), base=base, now=NOW)
    events = published_events(base)
    assert len(events) >= 2
    return events


def _with_category(events: list[dict]) -> dict:
    return next(e for e in events if e.get("categories"))


def test_unpublish_removes_event_everywhere(tmp_path):
    events = _published(tmp_path)
    target = _with_category(events)
    unpublish(target["id"], base=tmp_path, now=NOW)

    public = tmp_path / "public"
    ids = [e["id"] for e in _load(public / "events.json")]
    assert target["id"] not in ids
    assert len(ids) == len(events) - 1
    assert target["id"] not in (public / "feeds" / "all.ics").read_text(encoding="utf-8")
    for cat in target["categories"]:
        assert target["id"] not in (public / "feeds" / f"{cat}.ics").read_text(encoding="utf-8")
    assert target["title"] not in (public / "digest.md").read_text(encoding="utf-8")
    # The other events are untouched.
    other = next(e for e in events if e["id"] != target["id"])
    assert other["id"] in (public / "feeds" / "all.ics").read_text(encoding="utf-8")


def test_unpublish_is_logged(tmp_path):
    target = _published(tmp_path)[0]
    unpublish(target["id"], base=tmp_path, now=NOW, reason="Feil aldersgruppe")
    info = _load(tmp_path / "public" / "published.json")
    assert info["unpublished"][-1]["id"] == target["id"]
    assert info["unpublished"][-1]["reason"] == "Feil aldersgruppe"
    assert info["events_published"] == len(published_events(tmp_path))
    assert info["runs"]  # approval history is kept
    assert load_blocked(tmp_path)[-1]["id"] == target["id"]


def test_reason_has_contact_details_removed(tmp_path):
    target = _published(tmp_path)[0]
    unpublish(target["id"], base=tmp_path, now=NOW, reason="Klage fra ola@example.no, 912 34 567")
    for path in (tmp_path / "blocked.json", tmp_path / "public" / "published.json"):
        text = path.read_text(encoding="utf-8")
        assert "ola@example.no" not in text and "912 34 567" not in text


def test_unknown_id_changes_nothing(tmp_path):
    _published(tmp_path)
    before = (tmp_path / "public" / "events.json").read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        unpublish("kn:does-not-exist", base=tmp_path, now=NOW)
    assert (tmp_path / "public" / "events.json").read_text(encoding="utf-8") == before
    assert load_blocked(tmp_path) == []


def test_nothing_published_yet(tmp_path):
    with pytest.raises(RuntimeError):
        unpublish("kn:1", base=tmp_path, now=NOW)


def test_next_run_rejects_the_unpublished_event(tmp_path):
    target = _published(tmp_path)[0]
    unpublish(target["id"], base=tmp_path, now=NOW)

    run_dir = _run(tmp_path)
    rejected = {e["id"]: e["reasons"] for e in _load(run_dir / "rejected.json")}
    assert rejected[target["id"]] == [UNPUBLISHED]
    for name in ("events.json", "needs_review.json", "not_for_youth.json"):
        assert target["id"] not in [e["id"] for e in _load(run_dir / name)]
    # Not a source problem: the kill switch ratio ignores it.
    report = _load(run_dir / "report.json")
    assert not report["halted"]
    assert report["rejection_reasons"][UNPUBLISHED] == 1

    approve(run_dir, base=tmp_path, now=NOW)
    assert target["id"] not in [e["id"] for e in published_events(tmp_path)]


def test_copy_with_new_id_is_also_blocked(tmp_path):
    target = _published(tmp_path)[0]
    unpublish(target["id"], base=tmp_path, now=NOW)

    # The same event sent in again under another ID (same title, date, venue).
    data = _load(FIXTURE)
    source_id = target["id"].split(":", 1)[1]
    for rec in data["events"]:
        if str(rec["id"]) == source_id:
            rec["id"] = "copy-999"
    copy = tmp_path / "copy.json"
    copy.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    run_dir = _run(tmp_path, offline_file=copy)
    rejected = {e["id"]: e["reasons"] for e in _load(run_dir / "rejected.json")}
    assert any(eid.endswith("copy-999") and r == [UNPUBLISHED] for eid, r in rejected.items())


def test_run_staged_before_unpublish_does_not_bring_it_back(tmp_path):
    target = _published(tmp_path)[0]
    staged_earlier = _run(tmp_path)  # staged while the event was still published
    unpublish(target["id"], base=tmp_path, now=NOW)
    approve(staged_earlier, base=tmp_path, now=NOW)
    assert target["id"] not in [e["id"] for e in published_events(tmp_path)]


def test_web_page_stops_showing_it(tmp_path):
    events = _published(tmp_path)
    target = next(e for e in events if sum(x["title"] == e["title"] for x in events) == 1)
    client = create_app(public_dir=tmp_path / "public", now_fn=lambda: NOW).test_client()
    assert target["title"] in client.get("/").get_data(as_text=True)
    unpublish(target["id"], base=tmp_path, now=NOW)
    assert target["title"] not in client.get("/").get_data(as_text=True)


# ---------------------------------------------------------------- command line

def test_cli_lists_published_events(tmp_path, monkeypatch, capsys):
    events = _published(tmp_path)
    monkeypatch.setattr(cli, "OUT_DIR", tmp_path)
    assert cli.main(["unpublish"]) == 0
    out = capsys.readouterr().out
    for ev in events:
        assert ev["id"] in out


def test_cli_unpublishes_after_confirmation(tmp_path, monkeypatch, capsys):
    target = _published(tmp_path)[0]
    monkeypatch.setattr(cli, "OUT_DIR", tmp_path)

    monkeypatch.setattr("builtins.input", lambda *_: "n")
    assert cli.main(["unpublish", target["id"]]) == 1
    assert target["id"] in [e["id"] for e in published_events(tmp_path)]

    monkeypatch.setattr("builtins.input", lambda *_: "y")
    assert cli.main(["unpublish", target["id"], "--reason", "test"]) == 0
    assert target["id"] not in [e["id"] for e in published_events(tmp_path)]


def test_cli_unknown_id(tmp_path, monkeypatch):
    _published(tmp_path)
    monkeypatch.setattr(cli, "OUT_DIR", tmp_path)
    assert cli.main(["unpublish", "kn:nope", "--yes"]) == 1
