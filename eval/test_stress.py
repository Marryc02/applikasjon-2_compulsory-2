"""Stress test 2 (dependency failure): regression checks for repairs R1-R3.

R1  unreadable source data (not JSON / wrong wrapper) -> clear stop message, no crash
R2  records that aren't events -> rejected one by one as invalid_record, no crash
R3  kill-switch message names the most common reason and a likely cause
R4  (unchanged) the 50 % reject limit; half-broken data still goes to a human
"""
import json
from pathlib import Path

import pytest

from harness.config import load_config
from harness.pipeline import run
from harness.sources import SourceFormatError, load_file
from eval.stress_source import NOW, STRESS_DIR, run_case

QUIET = dict(log=lambda *_: None)


def _valid(n=3):
    from harness.sources.synthetic import generate
    recs = [r for r in generate(NOW) if r["_expected"]["outcome"] == "accepted"][:n]
    for r in recs:
        r.pop("_expected")
    return recs


def _write(tmp_path, data, name="in.json"):
    p = tmp_path / name
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return p


# --- R1 -------------------------------------------------------------------
def test_not_json_gives_clear_error(tmp_path):
    with pytest.raises(SourceFormatError, match="isn't valid JSON.*Nothing was staged"):
        load_file(_write(tmp_path, '{"events": [{"id": "1", "title": "Kon'))


def test_wrong_wrapper_gives_clear_error(tmp_path):
    with pytest.raises(SourceFormatError, match="no 'events' list \\(found: data\\)"):
        load_file(_write(tmp_path, {"data": _valid()}))


def test_events_not_a_list(tmp_path):
    with pytest.raises(SourceFormatError, match="not a list"):
        load_file(_write(tmp_path, {"events": "none today"}))


def test_list_and_wrapper_still_load(tmp_path):
    assert len(load_file(_write(tmp_path, _valid(), "a.json"))) == 3
    assert len(load_file(_write(tmp_path, {"events": _valid()}, "b.json"))) == 3
    assert load_file(_write(tmp_path, {"events": []}, "c.json")) == []


# --- R2 -------------------------------------------------------------------
def test_garbage_records_are_rejected_not_crashing(tmp_path):
    f = _write(tmp_path, {"events": ["Konsert, ring 912 34 567", 42, None, *_valid(5)]})
    report = run(load_config(), NOW, offline_file=f, classifier="baseline", base=tmp_path, **QUIET)
    assert report["rejection_reasons"]["invalid_record"] == 3
    assert not report["halted"]  # 3 of 8 rejected is under the limit
    rejected = json.loads((tmp_path / "staging" / report["run_id"] / "rejected.json").read_text(encoding="utf-8"))
    bad = [r for r in rejected if r["reasons"] == ["invalid_record"]]
    assert [r["id"] for r in bad] == ["invalid-record-1", "invalid-record-2", "invalid-record-3"]
    assert "912" not in bad[0]["preview"]  # privacy filter also covers broken records


# --- R3 -------------------------------------------------------------------
def test_halt_message_names_reason_and_cause(tmp_path):
    recs = _valid(4)
    for r in recs:
        r["navn"] = r.pop("tittel")  # the source renamed a field
    f = _write(tmp_path, {"events": recs})
    report = run(load_config(), NOW, offline_file=f, classifier="baseline", base=tmp_path, **QUIET)
    assert report["halted"]
    msg = report["halted_reason"]
    assert "missing_field:title" in msg and "changed its format" in msg
    assert "staged" not in msg  # the log line says it once, not twice


# --- Regression over every stress input ------------------------------------
@pytest.mark.skipif(not any(STRESS_DIR.glob("*.json")), reason="run python -m eval.make_stress_inputs first")
def test_no_stress_input_crashes_and_only_half_broken_is_staged(tmp_path):
    results = {p.stem: run_case(p.stem, tmp_path / p.stem, offline_file=p) for p in sorted(STRESS_DIR.glob("*.json"))}
    assert not [n for n, r in results.items() if r["status"] == "CRASH"]
    assert [n for n, r in results.items() if r["staged_for_approval"]] == ["09_half_missing_dates"]
    assert results["02_not_json"]["status"] == results["03_wrong_wrapper"]["status"] == "source_unreadable"
