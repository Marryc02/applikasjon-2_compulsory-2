"""End-to-end checks: run the whole pipeline on the labelled synthetic fixture.

These tests check what code must get exactly right (rejections, duplicates,
privacy, approval gate, kill switch). How well the *classifier* does is measured
separately by `python -m eval.run_eval`, so a weaker classifier shows up as a
lower score there, not as a failing test here.
"""
import copy
import json
from datetime import datetime
from pathlib import Path

from harness.config import OSLO, load_config
from harness.pipeline import run
from harness.publish import approve, latest_ready_run
from harness.sources.synthetic import generate

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "kulturnett_SYNTHETIC_2026-11-02.json"
NOW = datetime(2026, 11, 2, 8, 0, tzinfo=OSLO)
QUIET = dict(log=lambda *_: None)


def _load(run_dir, name):
    return json.loads((run_dir / name).read_text(encoding="utf-8"))


def _expected():
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))["events"]
    return {f"kn:{r['id']}": r["_expected"] for r in records}


def _run(tmp_path, cfg=None, **kw):
    report = run(cfg or load_config(), NOW, offline_file=kw.pop("offline_file", FIXTURE),
                 classifier="baseline", base=tmp_path, **QUIET, **kw)
    return report, tmp_path / "staging" / report["run_id"]


def test_fixture_matches_generator():
    """The saved fixture must be exactly what the generator makes for NOW."""
    saved = json.loads(FIXTURE.read_text(encoding="utf-8"))["events"]
    assert saved == json.loads(json.dumps(generate(NOW)))


def test_rejections_and_duplicates_match_labels(tmp_path):
    report, run_dir = _run(tmp_path)
    assert not report["halted"]
    expected = _expected()

    rejected = {e["id"]: e["reasons"] for e in _load(run_dir, "rejected.json")}
    want_rejected = {i: x["reason"] for i, x in expected.items() if x["outcome"] == "rejected"}
    assert set(rejected) == set(want_rejected)
    for ev_id, reason in want_rejected.items():
        assert reason in rejected[ev_id], ev_id

    dupes = {e["id"] for e in _load(run_dir, "duplicates.json")}
    assert dupes == {i for i, x in expected.items() if x["outcome"] == "duplicate"}


def test_every_event_is_accounted_for(tmp_path):
    _, run_dir = _run(tmp_path)
    ids = []
    for name in ("events", "not_for_youth", "needs_review", "duplicates", "rejected"):
        ids += [e["id"] for e in _load(run_dir, f"{name}.json")]
    assert sorted(ids) == sorted(_expected())  # nothing lost, nothing counted twice


def test_no_personal_data_or_labels_in_output(tmp_path):
    _, run_dir = _run(tmp_path)
    for path in run_dir.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert "@example.no" not in text and "912 34 567" not in text, path.name
            assert "_expected" not in text, path.name


def test_feeds(tmp_path):
    _, run_dir = _run(tmp_path)
    accepted = _load(run_dir, "events.json")
    all_ics = (run_dir / "feeds" / "all.ics").read_text(encoding="utf-8")
    assert all_ics.count("BEGIN:VEVENT") == len(accepted)
    for ev in accepted:
        for cat in ev["categories"]:
            assert ev["id"] in (run_dir / "feeds" / f"{cat}.ics").read_text(encoding="utf-8")


def test_nothing_is_public_before_approval(tmp_path):
    _run(tmp_path)
    assert not (tmp_path / "public").exists()
    public = approve(latest_ready_run(tmp_path), base=tmp_path)
    assert (public / "feeds" / "all.ics").exists()
    assert latest_ready_run(tmp_path) is None  # can't approve the same run twice


def test_kill_switch_halts_run(tmp_path):
    cfg = copy.deepcopy(load_config())
    cfg["safety"]["max_reject_ratio"] = 0.2  # fixture has ~32 % rejects
    report, run_dir = _run(tmp_path, cfg)
    assert report["halted"]
    assert not (run_dir / "READY_FOR_APPROVAL").exists()
    assert not (run_dir / "events.json").exists()


def test_kill_switch_on_empty_source(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text('{"events": []}', encoding="utf-8")
    report, _ = _run(tmp_path, offline_file=empty)
    assert report["halted"] and report["halted_reason"] == "too_few_events_collected"
