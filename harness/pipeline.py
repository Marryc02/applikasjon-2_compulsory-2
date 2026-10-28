"""Runs the stages in order and writes a log of what each stage did."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .classify import BaselineClassifier, LLMClassifier, classify_all, load_categories
from .config import OUT_DIR, get_secret
from .dedupe import dedupe
from .fetch_ticketmaster import fetch_live, load_offline
from .normalize import normalize_ticketmaster
from .publish import stage_run
from .validate import validate_categories, validate_event


def run(cfg: dict, now: datetime, offline_file: Path | None = None,
        classifier: str = "auto", base: Path = OUT_DIR, log=print) -> dict:
    run_id = now.strftime("%Y%m%d-%H%M%S")
    allowed, categories_text = load_categories()

    # 1. Collect
    if offline_file:
        raw = load_offline(offline_file)
        source = f"offline:{Path(offline_file).name}"
    else:
        api_key = get_secret("TICKETMASTER_API_KEY")
        if not api_key:
            raise SystemExit("TICKETMASTER_API_KEY is not set. Use --offline to run on sample data.")
        raw = fetch_live(cfg, now, api_key)
        source = "ticketmaster:live"
    raw_dir = base / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    # Saved in the API's own shape, so a live response can be copied to
    # fixtures/ and replayed offline with --offline <file>.
    saved = {"_comment": f"Saved from {source} at {now.isoformat()}", "_embedded": {"events": raw}}
    (raw_dir / f"{run_id}.json").write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[1 collect]   {len(raw)} events from {source}")

    # 2. Normalize
    events = [normalize_ticketmaster(e) for e in raw]
    log(f"[2 normalize] {len(events)} events, {sum('pii_removed' in e['flags'] for e in events)} had contact info removed")

    # 3. Validate
    valid, rejected = [], []
    for ev in events:
        reasons = validate_event(ev, cfg, now)
        (rejected.append({**ev, "reasons": reasons}) if reasons else valid.append(ev))
    log(f"[3 validate]  {len(valid)} valid, {len(rejected)} rejected")

    # Kill switch: a sudden flood of invalid events means something upstream is
    # broken (API change, bad config, wrong area). Stop instead of publishing.
    reject_ratio = len(rejected) / len(events) if events else 1.0
    halted_reason = None
    if len(events) < cfg["safety"]["min_events_fetched"]:
        halted_reason = "too_few_events_fetched"
    elif reject_ratio > cfg["safety"]["max_reject_ratio"]:
        halted_reason = f"reject_ratio {reject_ratio:.2f} > {cfg['safety']['max_reject_ratio']}"

    # 4. Dedupe
    unique, duplicates = dedupe(valid)
    log(f"[4 dedupe]    {len(unique)} unique, {len(duplicates)} duplicates removed")

    # 5. Classify
    baseline = BaselineClassifier(allowed)
    anthropic_key = get_secret("ANTHROPIC_API_KEY")
    if classifier == "llm" or (classifier == "auto" and anthropic_key):
        if not anthropic_key:
            raise SystemExit("ANTHROPIC_API_KEY is not set (needed for --classifier llm).")
        primary = LLMClassifier(allowed, categories_text, cfg, anthropic_key)
    else:
        primary = baseline
    class_stats = classify_all(unique, primary, baseline) if not halted_reason else {"classifier": "skipped"}
    accepted, needs_review = [], []
    for ev in unique:
        problems = validate_categories(ev, allowed)
        (needs_review.append({**ev, "reasons": problems}) if problems else accepted.append(ev))
    log(f"[5 classify]  by {class_stats['classifier']}: {len(accepted)} categorized, {len(needs_review)} need review")

    # 6. Stage for human approval
    report = {
        "run_id": run_id,
        "run_time": now.isoformat(),
        "source": source,
        "counts": {
            "fetched": len(raw), "valid": len(valid), "rejected": len(rejected),
            "duplicates": len(duplicates), "accepted": len(accepted), "needs_review": len(needs_review),
        },
        "reject_ratio": round(reject_ratio, 3),
        "rejection_reasons": _count_reasons(rejected),
        "classification": class_stats,
        "halted": halted_reason is not None,
        "halted_reason": halted_reason,
    }
    run_dir = stage_run(run_id, accepted, rejected, duplicates, needs_review, report, sorted(allowed), now, base)
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
