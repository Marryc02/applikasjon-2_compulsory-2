"""End-to-end test: run the whole pipeline on the synthetic fixture and check
every event lands where expected. This is the start of the evaluation harness."""
import copy
import json
from datetime import datetime
from pathlib import Path

from harness.config import OSLO, load_config
from harness.pipeline import run
from harness.publish import approve, latest_ready_run

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "ticketmaster_sample_SYNTHETIC.json"
NOW = datetime(2026, 11, 2, 8, 0, tzinfo=OSLO)

EXPECTED_ACCEPTED = {
    "tm:SYN001": ["music"],
    "tm:SYN002": ["sports"],
    "tm:SYN003": ["gaming"],
    "tm:SYN009": ["arts_culture"],
    "tm:SYN011": ["social"],
}
EXPECTED_REJECTED = {
    "tm:SYN005": "outside_area",
    "tm:SYN006": "in_past",
    "tm:SYN007": "status_not_active",
    "tm:SYN008": "missing_field:venue_name",
    "tm:SYN010": "too_far_ahead",
    "tm:SYN012": "date_tbd",
}


def _load(run_dir, name):
    return json.loads((run_dir / name).read_text(encoding="utf-8"))


def test_offline_run_end_to_end(tmp_path):
    report = run(load_config(), NOW, FIXTURE, classifier="baseline", base=tmp_path, log=lambda *_: None)
    assert not report["halted"]
    run_dir = tmp_path / "staging" / report["run_id"]

    accepted = {e["id"]: e["categories"] for e in _load(run_dir, "events.json")}
    assert accepted == EXPECTED_ACCEPTED

    rejected = {e["id"]: e["reasons"] for e in _load(run_dir, "rejected.json")}
    assert set(rejected) == set(EXPECTED_REJECTED)
    for ev_id, reason in EXPECTED_REJECTED.items():
        assert reason in rejected[ev_id], ev_id

    assert [d["id"] for d in _load(run_dir, "duplicates.json")] == ["tm:SYN004"]

    # No contact details survive into published output.
    published_text = (run_dir / "events.json").read_text(encoding="utf-8")
    assert "@example.no" not in published_text and "912 34 567" not in published_text

    # Category feeds contain exactly the right events.
    gaming = (run_dir / "feeds" / "gaming.ics").read_text(encoding="utf-8")
    assert gaming.count("BEGIN:VEVENT") == 1 and "SYN003" in gaming
    assert (run_dir / "feeds" / "all.ics").read_text(encoding="utf-8").count("BEGIN:VEVENT") == 5


def test_nothing_is_public_before_approval(tmp_path):
    run(load_config(), NOW, FIXTURE, classifier="baseline", base=tmp_path, log=lambda *_: None)
    assert not (tmp_path / "public").exists()
    public = approve(latest_ready_run(tmp_path), base=tmp_path)
    assert (public / "feeds" / "all.ics").exists()
    assert latest_ready_run(tmp_path) is None  # can't approve the same run twice


def test_kill_switch_halts_run(tmp_path):
    cfg = copy.deepcopy(load_config())
    cfg["safety"]["max_reject_ratio"] = 0.2  # fixture has 50 % rejects
    report = run(cfg, NOW, FIXTURE, classifier="baseline", base=tmp_path, log=lambda *_: None)
    assert report["halted"]
    run_dir = tmp_path / "staging" / report["run_id"]
    assert not (run_dir / "READY_FOR_APPROVAL").exists()
    assert not (run_dir / "events.json").exists()
