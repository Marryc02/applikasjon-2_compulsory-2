"""Runs the stages in order and writes a log of what each stage did."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .classify import BaselineClassifier, LLMClassifier, classify_all, load_categories
from .config import OUT_DIR, get_secret
from .dedupe import dedupe
from .publish import stage_run
from .sources import collect
from .sources.kulturnett import normalize
from .validate import validate_classification, validate_event


def run(cfg: dict, now: datetime, source: str = "synthetic", offline_file: Path | None = None,
        classifier: str = "auto", base: Path = OUT_DIR, log=print) -> dict:
    run_id = now.strftime("%Y%m%d-%H%M%S")
    allowed, categories_text = load_categories()

    # 1. Collect
    raw, source_desc = collect(source, cfg, now, offline_file)
    raw_dir = base / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    # Saved as {"events": [...]}, so it can be copied to fixtures/ and replayed with --offline.
    saved = {"_comment": f"Collected from {source_desc} at {now.isoformat()}", "events": raw}
    (raw_dir / f"{run_id}.json").write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[1 collect]   {len(raw)} events from {source_desc}")

    # 2. Normalize (drops test labels such as _expected)
    events = [normalize(r) for r in raw]
    log(f"[2 normalize] {len(events)} events, {sum('pii_removed' in e['flags'] for e in events)} had contact info removed")

    # 3. Validate
    valid, rejected = [], []
    for ev in events:
        reasons = validate_event(ev, cfg, now)
        (rejected.append({**ev, "reasons": reasons}) if reasons else valid.append(ev))
    log(f"[3 validate]  {len(valid)} valid, {len(rejected)} rejected")

    # Kill switch: a flood of invalid events means something upstream is broken
    # (format change, bad config, wrong area). Stop instead of publishing.
    reject_ratio = len(rejected) / len(events) if events else 1.0
    halted_reason = None
    if len(events) < cfg["safety"]["min_events_collected"]:
        halted_reason = "too_few_events_collected"
    elif reject_ratio > cfg["safety"]["max_reject_ratio"]:
        halted_reason = f"reject_ratio {reject_ratio:.2f} > {cfg['safety']['max_reject_ratio']}"

    # 4. Dedupe
    unique, duplicates = dedupe(valid)
    log(f"[4 dedupe]    {len(unique)} unique, {len(duplicates)} duplicates removed")

    # 5. Classify: for youth? which categories?
    baseline = BaselineClassifier(allowed)
    anthropic_key = get_secret("ANTHROPIC_API_KEY")
    if classifier == "llm" or (classifier == "auto" and anthropic_key):
        if not anthropic_key:
            raise SystemExit("ANTHROPIC_API_KEY is not set (needed for --classifier llm).")
        primary = LLMClassifier(allowed, categories_text, cfg, anthropic_key)
    else:
        primary = baseline
    class_stats = classify_all(unique, primary, baseline) if not halted_reason else {"classifier": "skipped"}

    accepted, not_for_youth, needs_review = [], [], []
    for ev in unique:
        if ev.get("youth") == "no":
            not_for_youth.append(ev)
            continue
        problems = validate_classification(ev, allowed)
        (needs_review.append({**ev, "reasons": problems}) if problems else accepted.append(ev))
    log(f"[5 classify]  by {class_stats['classifier']}: {len(accepted)} for youth, "
        f"{len(not_for_youth)} not for youth, {len(needs_review)} need review")

    # 6. Stage for human approval
    report = {
        "run_id": run_id,
        "run_time": now.isoformat(),
        "source": source_desc,
        "counts": {
            "collected": len(raw), "valid": len(valid), "rejected": len(rejected),
            "duplicates": len(duplicates), "accepted": len(accepted),
            "not_for_youth": len(not_for_youth), "needs_review": len(needs_review),
        },
        "reject_ratio": round(reject_ratio, 3),
        "rejection_reasons": _count_reasons(rejected),
        "classification": class_stats,
        "halted": halted_reason is not None,
        "halted_reason": halted_reason,
    }
    outputs = {"rejected": rejected, "duplicates": duplicates, "not_for_youth": not_for_youth,
               "needs_review": needs_review}
    run_dir = stage_run(run_id, accepted, outputs, report, sorted(allowed), now, base)
    if halted_reason:
        log(f"[6 stage]     HALTED by kill switch: {halted_reason}. Nothing staged for approval.")
    else:
        log(f"[6 stage]     staged in {run_dir}")
        log("              review it, then run: python -m harness approve")
    return report


def _count_reasons(rejected: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for ev in rejected:
        for r in ev["reasons"]:
            counts[r] = counts.get(r, 0) + 1
    return dict(sorted(counts.items()))
