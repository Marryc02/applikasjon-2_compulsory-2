"""Generate the broken source inputs for stress test 2 (dependency failure).

    python -m eval.make_stress_inputs

Writes fixtures/stress/*.json. Each file simulates a way the Kulturnett source
could misbehave. They are built from the synthetic generator (run time
2026-11-02 08:00), so they are reproducible. All events are made up.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime

from harness.config import OSLO, ROOT
from harness.sources.synthetic import generate

NOW = datetime(2026, 11, 2, 8, 0, tzinfo=OSLO)
OUT = ROOT / "fixtures" / "stress"


def _valid_records() -> list[dict]:
    """Synthetic events that pass validation (drop labels; keep only labelled-accepted/not_youth/review)."""
    keep = {"accepted", "not_youth", "needs_review"}
    recs = [r for r in generate(NOW) if r["_expected"]["outcome"] in keep]
    for r in recs:
        r.pop("_expected", None)
    return recs


def _write(name: str, data, comment: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    if isinstance(data, str):  # deliberately broken text
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps({"_comment": comment, **data}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")


def main() -> None:
    valid = _valid_records()

    _write("01_empty", {"events": []}, "Source answers, but with no events.")

    _write("02_not_json", '{"events": [ {"id": "1", "tittel": "Konsert", "start": "2026-11-0',
           "")  # response cut off mid-transfer

    _write("03_wrong_wrapper", {"data": valid}, "Events delivered under 'data' instead of 'events'.")

    _write("04_garbage_records", {"events": ["Konsert", 42, None, ["a", "b"]] + valid[:2]},
           "Some records are not objects at all.")

    renamed = []
    for r in copy.deepcopy(valid):
        r["title"] = r.pop("tittel")
        r["place"] = r.pop("sted")
        r["link"] = r.pop("url")
        renamed.append(r)
    _write("05_renamed_fields", {"events": renamed},
           "Source renamed fields (tittel->title, sted->place, url->link): a format change.")

    other_dates = copy.deepcopy(valid)
    for r in other_dates:
        if r.get("start") and "T" in r["start"]:
            d = datetime.fromisoformat(r["start"])
            r["start"] = d.strftime("%d.%m.%Y %H:%M")  # Norwegian style instead of ISO 8601
    _write("06_norwegian_dates", {"events": other_dates},
           "Source switched to Norwegian date format (05.11.2026 19:00).")

    wrong_area = copy.deepcopy(valid)
    for r in wrong_area:
        if r.get("sted"):
            r["sted"] = {**r["sted"], "kommune": "Lillehammer"}
    _write("07_wrong_region", {"events": wrong_area},
           "Source returns events for the wrong region (all in Lillehammer).")

    mostly_bad = copy.deepcopy(valid)
    for r in mostly_bad[: int(len(mostly_bad) * 0.6) + 1]:
        r["start"] = None
    _write("08_mostly_missing_dates", {"events": mostly_bad},
           "Just over half the events have no start time.")

    half_bad = copy.deepcopy(valid)
    n = len(half_bad)
    for r in half_bad[: n // 2]:
        r["start"] = None
    _write("09_half_missing_dates", {"events": half_bad},
           "Exactly half (or just under) the events have no start time: the kill-switch boundary.")


if __name__ == "__main__":
    main()
