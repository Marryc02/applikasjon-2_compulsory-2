"""Evaluation run (first version): run the pipeline on a labelled fixture and
compare every event's outcome with its `_expected` label.

    python -m eval.run_eval [--fixture FILE] [--now ISO] [--classifier baseline|llm]

Writes out/eval/<timestamp>.json and prints a summary. Exit code 1 if any
mechanically decidable outcome (rejected / duplicate) is wrong.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from harness.config import OSLO, OUT_DIR, ROOT, load_config, load_dotenv
from harness.pipeline import run

DEFAULT_FIXTURE = ROOT / "fixtures" / "kulturnett_SYNTHETIC_2026-11-02.json"
DEFAULT_NOW = "2026-11-02T08:00:00+01:00"
OUTCOME_FILES = {"events": "accepted", "not_for_youth": "not_youth", "needs_review": "needs_review",
                 "duplicates": "duplicate", "rejected": "rejected"}
MECHANICAL = {"rejected", "duplicate"}


def evaluate(fixture: Path, now: datetime, classifier: str, base: Path) -> dict:
    records = json.loads(fixture.read_text(encoding="utf-8"))["events"]
    expected = {f"kn:{r['id']}": r["_expected"] for r in records}
    report = run(load_config(), now, offline_file=fixture, classifier=classifier, base=base, log=lambda *_: None)
    run_dir = base / "staging" / report["run_id"]

    actual: dict[str, dict] = {}
    for fname, outcome in OUTCOME_FILES.items():
        path = run_dir / f"{fname}.json"
        if path.exists():
            for ev in json.loads(path.read_text(encoding="utf-8")):
                actual[ev["id"]] = {"outcome": outcome, "categories": ev.get("categories", []),
                                    "reasons": ev.get("reasons", [])}

    rows, cat_tp, cat_fp, cat_fn = [], {}, {}, {}
    for ev_id, exp in expected.items():
        got = actual.get(ev_id, {"outcome": "missing", "categories": [], "reasons": []})
        ok = got["outcome"] == exp["outcome"]
        if ok and exp["outcome"] == "rejected":
            ok = exp["reason"] in got["reasons"]
        if exp["outcome"] == "accepted" and got["outcome"] == "accepted":
            e, g = set(exp["categories"]), set(got["categories"])
            for c in e | g:
                cat_tp[c] = cat_tp.get(c, 0) + (c in e and c in g)
                cat_fp[c] = cat_fp.get(c, 0) + (c in g and c not in e)
                cat_fn[c] = cat_fn.get(c, 0) + (c in e and c not in g)
        rows.append({"id": ev_id, "expected": exp, "got": got, "outcome_correct": ok})

    per_category = {}
    for c in sorted(set(cat_tp) | set(cat_fp) | set(cat_fn)):
        tp, fp, fn = cat_tp.get(c, 0), cat_fp.get(c, 0), cat_fn.get(c, 0)
        per_category[c] = {"precision": round(tp / (tp + fp), 3) if tp + fp else None,
                           "recall": round(tp / (tp + fn), 3) if tp + fn else None, "tp": tp, "fp": fp, "fn": fn}

    mech = [r for r in rows if r["expected"]["outcome"] in MECHANICAL]
    judg = [r for r in rows if r["expected"]["outcome"] not in MECHANICAL]
    return {
        "fixture": fixture.name, "run_time": now.isoformat(), "classifier": report["classification"]["classifier"],
        "n_events": len(rows),
        "outcome_accuracy": round(sum(r["outcome_correct"] for r in rows) / len(rows), 3),
        "mechanical_correct": f"{sum(r['outcome_correct'] for r in mech)}/{len(mech)}",
        "judgement_correct": f"{sum(r['outcome_correct'] for r in judg)}/{len(judg)}",
        "per_category": per_category,
        "errors": [r for r in rows if not r["outcome_correct"]],
        "rows": rows,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    p.add_argument("--now", default=DEFAULT_NOW)
    p.add_argument("--classifier", choices=["baseline", "llm"], default="baseline")
    args = p.parse_args(argv)
    load_dotenv()

    now = datetime.fromisoformat(args.now)
    stamp = datetime.now(OSLO).strftime("%Y%m%d-%H%M%S")
    base = OUT_DIR / "eval" / f"{stamp}-{args.classifier}"
    result = evaluate(args.fixture, now, args.classifier, base)
    (OUT_DIR / "eval").mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / "eval" / f"{stamp}-{args.classifier}.json"
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Fixture: {result['fixture']}   classifier: {result['classifier']}   events: {result['n_events']}")
    print(f"Outcome accuracy:       {result['outcome_accuracy']:.1%}")
    print(f"  mechanical (code):    {result['mechanical_correct']}")
    print(f"  judgement (classify): {result['judgement_correct']}")
    print("Categories (accepted events):  precision / recall")
    for c, m in result["per_category"].items():
        print(f"  {c:13} {m['precision']!s:>6} / {m['recall']!s:<6}  (tp {m['tp']}, fp {m['fp']}, fn {m['fn']})")
    for e in result["errors"]:
        print(f"  WRONG {e['id']}: expected {e['expected']}, got {e['got']['outcome']} {e['got']['reasons']}")
    print(f"Full results: {out_file}")
    mech_ok, mech_n = map(int, result["mechanical_correct"].split("/"))
    return 0 if mech_ok == mech_n else 1


if __name__ == "__main__":
    sys.exit(main())
