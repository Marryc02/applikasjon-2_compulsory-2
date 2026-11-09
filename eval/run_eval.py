"""Evaluation run: run the pipeline on a labelled fixture and compare every
event's outcome with its `_expected` label.

    python -m eval.run_eval [--fixture FILE] [--now ISO] [--classifier baseline|llm]
                            [--repeat N] [--check-only]

Before anything runs, the fixture's labels are checked and every problem is
reported with the event id (exit code 2). `--repeat N` runs the same fixture N
times and reports which events changed outcome between runs (model variance).

Writes out/eval/<timestamp>-<classifier>.json and prints a summary. Exit code 1
if any mechanically decidable outcome (rejected / duplicate) is wrong.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from harness.classify import load_categories
from harness.config import OSLO, OUT_DIR, ROOT, load_config, load_dotenv
from harness.pipeline import run
from harness.validate import REQUIRED

DEFAULT_FIXTURE = ROOT / "fixtures" / "kulturnett_SYNTHETIC_2026-11-02.json"
DEFAULT_NOW = "2026-11-02T08:00:00+01:00"
OUTCOME_FILES = {"events": "accepted", "not_for_youth": "not_youth", "needs_review": "needs_review",
                 "duplicates": "duplicate", "rejected": "rejected"}
MECHANICAL = {"rejected", "duplicate"}

# What a label may contain, per outcome.
LABEL_KEYS = {
    "accepted": {"outcome", "categories", "youth"},
    "not_youth": {"outcome"},
    "needs_review": {"outcome"},
    "duplicate": {"outcome"},
    "rejected": {"outcome", "reason"},
}
REJECT_REASONS = {f"missing_field:{f}" for f in REQUIRED} | {
    "invalid_url", "status_not_active", "invalid_start", "in_past", "too_far_ahead", "outside_area"}


# ---------------------------------------------------------------- label check

def check_labels(fixture: Path) -> tuple[list[dict], list[str]]:
    """Load a fixture and check its labels. Returns (records, problems)."""
    try:
        data = json.loads(fixture.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [], [f"Not valid JSON: {e.msg} at line {e.lineno}, column {e.colno}. "
                    "Often a missing or extra comma, bracket or brace just before that point."]
    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        return [], ['The file must be an object with an "events" list: {"events": [ ... ]}']

    allowed, _ = load_categories()
    records, problems, seen = data["events"], [], {}
    for i, rec in enumerate(records, start=1):
        where = f"event #{i}" + (f" ({rec.get('id')})" if isinstance(rec, dict) and rec.get("id") else "")
        if not isinstance(rec, dict):
            problems.append(f"{where}: is not an object")
            continue
        rid = rec.get("id")
        if not rid:
            problems.append(f"{where}: needs a non-empty \"id\" so the result can be matched to the label")
        elif rid in seen:
            problems.append(f"{where}: id \"{rid}\" is also used by event #{seen[rid]}; every id must be unique")
        else:
            seen[rid] = i

        exp = rec.get("_expected")
        if not isinstance(exp, dict):
            problems.append(f"{where}: missing \"_expected\" label")
            continue
        outcome = exp.get("outcome")
        if outcome not in LABEL_KEYS:
            problems.append(f"{where}: outcome \"{outcome}\" is not one of {sorted(LABEL_KEYS)}")
            continue
        extra = set(exp) - LABEL_KEYS[outcome]
        if extra:
            problems.append(f"{where}: \"{outcome}\" labels must not have {sorted(extra)} "
                            "(categories and youth belong only on \"accepted\")")
        if outcome == "accepted":
            cats = exp.get("categories")
            if not isinstance(cats, list) or not 1 <= len(cats) <= 3:
                problems.append(f"{where}: \"accepted\" needs \"categories\": a list of 1–3 category ids")
            else:
                unknown = [c for c in cats if c not in allowed]
                if unknown:
                    problems.append(f"{where}: unknown categories {unknown}; allowed: {sorted(allowed)}")
            if exp.get("youth") != "yes":
                problems.append(f"{where}: \"accepted\" needs \"youth\": \"yes\"")
        if outcome == "rejected" and exp.get("reason") not in REJECT_REASONS:
            problems.append(f"{where}: \"rejected\" needs a \"reason\" from {sorted(REJECT_REASONS)}, "
                            f"got {exp.get('reason')!r}")
    return records, problems


# ---------------------------------------------------------------- evaluation

def evaluate(fixture: Path, now: datetime, classifier: str, base: Path, records: list[dict] | None = None) -> dict:
    if records is None:
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


def variance_summary(runs: list[dict]) -> dict:
    """Compare repeated runs: which events got a different outcome or categories between runs?"""
    by_event: dict[str, list] = {}
    for r in runs:
        for row in r["rows"]:
            by_event.setdefault(row["id"], []).append(
                (row["got"]["outcome"], tuple(sorted(row["got"]["categories"])), row["outcome_correct"]))
    unstable = []
    for ev_id, results in by_event.items():
        outcomes = sorted({o for o, _, _ in results})
        cats = sorted({c for _, c, _ in results})
        if len(outcomes) > 1 or len(cats) > 1:
            unstable.append({"id": ev_id, "outcomes": outcomes, "categories": [list(c) for c in cats],
                             "correct_in": f"{sum(ok for _, _, ok in results)}/{len(results)}"})
    judg = [int(r["judgement_correct"].split("/")[0]) for r in runs]
    return {
        "n_runs": len(runs),
        "judgement_correct_per_run": [r["judgement_correct"] for r in runs],
        "judgement_correct_min": min(judg), "judgement_correct_max": max(judg),
        "judgement_correct_mean": round(sum(judg) / len(judg), 2),
        "unstable_events": unstable,
    }


# ---------------------------------------------------------------- command line

def _print_result(result: dict) -> None:
    print(f"Outcome accuracy:       {result['outcome_accuracy']:.1%}")
    print(f"  mechanical (code):    {result['mechanical_correct']}")
    print(f"  judgement (classify): {result['judgement_correct']}")
    print("Categories (accepted events):  precision / recall")
    for c, m in result["per_category"].items():
        print(f"  {c:13} {m['precision']!s:>6} / {m['recall']!s:<6}  (tp {m['tp']}, fp {m['fp']}, fn {m['fn']})")
    for e in result["errors"]:
        print(f"  WRONG {e['id']}: expected {e['expected']}, got {e['got']['outcome']} {e['got']['reasons']}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    p.add_argument("--now", default=DEFAULT_NOW)
    p.add_argument("--classifier", choices=["baseline", "llm"], default="baseline")
    p.add_argument("--repeat", type=int, default=1, help="run the evaluation N times and compare (model variance)")
    p.add_argument("--check-only", action="store_true", help="only check the fixture's labels")
    args = p.parse_args(argv)
    load_dotenv()

    records, problems = check_labels(args.fixture)
    if problems:
        print(f"Label problems in {args.fixture.name}:")
        for prob in problems:
            print(f"  - {prob}")
        return 2
    print(f"Labels OK: {len(records)} events in {args.fixture.name}")
    if args.check_only:
        return 0
    if args.repeat < 1:
        print("--repeat must be at least 1")
        return 2

    now = datetime.fromisoformat(args.now)
    stamp = datetime.now(OSLO).strftime("%Y%m%d-%H%M%S")
    name = f"{stamp}-{args.classifier}" + (f"-x{args.repeat}" if args.repeat > 1 else "")
    base = OUT_DIR / "eval" / name
    runs = [evaluate(args.fixture, now, args.classifier, base / f"run{i}", records) for i in range(1, args.repeat + 1)]

    result = dict(runs[0])
    if args.repeat > 1:
        result = {"fixture": runs[0]["fixture"], "classifier": runs[0]["classifier"],
                  "variance": variance_summary(runs), "runs": runs}
    (OUT_DIR / "eval").mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / "eval" / f"{name}.json"
    out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Fixture: {runs[0]['fixture']}   classifier: {runs[0]['classifier']}   events: {runs[0]['n_events']}")
    if args.repeat == 1:
        _print_result(runs[0])
    else:
        v = result["variance"]
        print(f"Runs: {v['n_runs']}   judgement correct per run: {', '.join(v['judgement_correct_per_run'])}")
        print(f"  min {v['judgement_correct_min']}, max {v['judgement_correct_max']}, mean {v['judgement_correct_mean']}")
        if v["unstable_events"]:
            print("Events whose result changed between runs:")
            for u in v["unstable_events"]:
                print(f"  {u['id']}: outcomes {u['outcomes']}, categories {u['categories']}, "
                      f"correct in {u['correct_in']} runs")
        else:
            print("Every event got the same result in every run.")
    print(f"Full results: {out_file}")
    mech_ok = all(r["mechanical_correct"].split("/")[0] == r["mechanical_correct"].split("/")[1] for r in runs)
    return 0 if mech_ok else 1


if __name__ == "__main__":
    sys.exit(main())
