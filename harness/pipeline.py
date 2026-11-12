"""Runs the stages in order and writes a log of what each stage did."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .classify import BaselineClassifier, LLMClassifier, classify_all, load_categories
from .config import OSLO, OUT_DIR, get_secret
from .dedupe import dedupe
from .privacy import strip_pii
from .publish import UNPUBLISHED, is_blocked, load_blocked, stage_run
from .sources import collect
from .sources.kulturnett import normalize
from .validate import validate_classification, validate_event


def _new_run_id(base: Path) -> str:
    """Run ID = the real clock time when the run starts, also when --now pretends
    another time (that one is kept as run_time in report.json). So the newest run
    always has the highest ID, which is what review and approve pick by default."""
    stamp = datetime.now(OSLO).strftime("%Y%m%d-%H%M%S")
    run_id, n = stamp, 2
    while (base / "staging" / run_id).exists() or (base / "raw" / f"{run_id}.json").exists():
        run_id, n = f"{stamp}-{n}", n + 1  # two runs in the same second
    return run_id


def run(cfg: dict, now: datetime, source: str = "synthetic", offline_file: Path | None = None,
        classifier: str = "auto", base: Path = OUT_DIR, log=print) -> dict:
    run_id = _new_run_id(base)
    allowed, categories_text = load_categories()

    # 1. Collect
    raw, source_desc = collect(source, cfg, now, offline_file)
    raw_dir = base / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    # Saved as {"events": [...]}, so it can be copied to fixtures/testing/ and replayed with --offline (same run time).
    saved = {"_comment": f"Collected from {source_desc} at {now.isoformat()}",
             "_run_time": now.isoformat(), "events": raw}
    (raw_dir / f"{run_id}.json").write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"[1 collect]   {len(raw)} events from {source_desc}")

    # 2. Normalize (drops test labels such as _expected). A record that isn't an
    # event at all is rejected on its own instead of crashing the run (repair R2).
    events, invalid = [], []
    for i, rec in enumerate(raw, start=1):
        try:
            if not isinstance(rec, dict):
                raise TypeError(f"a {type(rec).__name__}, not an event")
            events.append(normalize(rec))
        except Exception as e:
            invalid.append({"id": f"invalid-record-{i}", "reasons": ["invalid_record"],
                            "detail": f"record #{i} is {e}" if isinstance(e, TypeError) else
                                      f"record #{i} could not be read: {type(e).__name__}: {e}",
                            "preview": strip_pii(repr(rec)[:120])[0], "flags": []})
    log(f"[2 normalize] {len(events)} events, {len(invalid)} unreadable records rejected, "
        f"{sum('pii_removed' in e['flags'] for e in events)} had contact info removed")

    # 3. Validate
    valid, rejected = [], list(invalid)
    for ev in events:
        reasons = validate_event(ev, cfg, now)
        (rejected.append({**ev, "reasons": reasons}) if reasons else valid.append(ev))
    log(f"[3 validate]  {len(valid)} valid, {len(rejected)} rejected")

    # Kill switch: a flood of invalid events means something upstream is broken
    # (format change, bad config, wrong area). Stop instead of publishing.
    total = len(raw)
    reject_ratio = len(rejected) / total if total else 1.0
    halted_reason = None
    if total < cfg["safety"]["min_events_collected"]:
        halted_reason = "too_few_events_collected"
    elif reject_ratio > cfg["safety"]["max_reject_ratio"]:
        halted_reason = _explain_halt(rejected, total, reject_ratio, cfg["safety"]["max_reject_ratio"])

    # 4. Dedupe
    unique, duplicates = dedupe(valid)
    log(f"[4 dedupe]    {len(unique)} unique, {len(duplicates)} duplicates removed")

    # Events a human has unpublished are not classified or staged again.
    # (After the kill-switch check, so they don't count as a source problem.)
    blocked_list = load_blocked(base)
    if blocked_list:
        kept = []
        for ev in unique:
            (rejected.append({**ev, "reasons": [UNPUBLISHED]}) if is_blocked(ev, blocked_list) else kept.append(ev))
        if len(kept) < len(unique):
            log(f"              {len(unique) - len(kept)} event(s) skipped: unpublished earlier by a human")
        unique = kept

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
        log(f"[6 stage]     HALTED by kill switch: {halted_reason.rstrip('.')}. Nothing staged for approval.")
    else:
        log(f"[6 stage]     staged in {run_dir}")
        log("              review it, then run: python -m harness approve")
    return report


def _explain_halt(rejected: list[dict], total: int, ratio: float, limit: float) -> str:
    """Kill-switch message that names the most common reason (repair R3)."""
    counts: dict[str, int] = {}
    for ev in rejected:
        for r in ev["reasons"]:
            counts[r] = counts.get(r, 0) + 1
    reason, n = max(counts.items(), key=lambda kv: kv[1])
    share = n / total
    msg = (f"{ratio:.0%} of events were rejected (limit {limit:.0%}). "
           f"Most common reason: {reason} ({share:.0%} of events).")
    if reason == "invalid_record":
        msg += " The source sent records that aren't events."
    elif share >= 0.9 and (reason.startswith("missing_field") or reason == "invalid_start"):
        msg += " The source may have changed its format."
    elif share >= 0.9 and reason == "outside_area":
        msg += " The source may be sending events for the wrong region."
    return msg  # the log line adds "Nothing staged for approval."


def _count_reasons(rejected: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for ev in rejected:
        for r in ev["reasons"]:
            counts[r] = counts.get(r, 0) + 1
    return dict(sorted(counts.items()))
