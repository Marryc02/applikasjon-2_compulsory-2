"""Stage 6 (stage) and stage 7 (publish after human approval).

The pipeline never publishes by itself. It writes a run to out/staging/<run_id>/.
A person reviews it and runs `python -m harness approve`, which adds its events
to out/public/. out/public/ holds every approved event that hasn't happened yet,
from all approved runs; the web page and the feeds are built from it.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from .config import OUT_DIR, OSLO
from .dedupe import dedupe_key
from .ics import build_calendar
from .privacy import strip_pii

DAYS_NO = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
MONTHS_NO = ["januar", "februar", "mars", "april", "mai", "juni", "juli",
             "august", "september", "oktober", "november", "desember"]


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_digest(events: list[dict], now: datetime) -> str:
    """Weekly digest in Norwegian: events in the next 7 days, grouped by day."""
    end = now + timedelta(days=7)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = sorted(
        (e for e in events
         if (today if e.get("all_day") else now) <= datetime.fromisoformat(e["start"]) < end),
        key=lambda e: e["start"],
    )
    out = ["# Denne uka for unge i Hamar", "",
           f"Arrangementer {now.day}. {MONTHS_NO[now.month - 1]} – {end.day}. {MONTHS_NO[end.month - 1]}.", ""]
    if not week:
        out.append("Ingen arrangementer funnet denne uka.")
    current_day = None
    for e in week:
        start = datetime.fromisoformat(e["start"]).astimezone(OSLO)
        day = start.date()
        if day != current_day:
            out += ["", f"## {DAYS_NO[start.weekday()].capitalize()} {start.day}. {MONTHS_NO[start.month - 1]}", ""]
            current_day = day
        cats = ", ".join(e.get("categories", []))
        when = "Hele dagen" if e.get("all_day") else f"{start:%H:%M}"
        out.append(f"- **{when}** [{e['title']}]({e['source_url']}), {e['venue_name']} ({cats})")
    out += ["", "_Automatisk satt sammen og godkjent av et menneske før publisering._", ""]
    return "\n".join(out)


def write_outputs(target: Path, events: list[dict], allowed: list[str], now: datetime) -> None:
    feeds = target / "feeds"
    feeds.mkdir(parents=True, exist_ok=True)
    _write_json(target / "events.json", events)
    (feeds / "all.ics").write_text(build_calendar(events, "Unge i Hamar – alle", now), encoding="utf-8", newline="")
    for cat in sorted(allowed):
        subset = [e for e in events if cat in e.get("categories", [])]
        (feeds / f"{cat}.ics").write_text(
            build_calendar(subset, f"Unge i Hamar – {cat}", now), encoding="utf-8", newline="")
    (target / "digest.md").write_text(build_digest(events, now), encoding="utf-8")


def stage_run(run_id: str, accepted: list[dict], outputs: dict[str, list[dict]], report: dict,
              allowed: list[str], now: datetime, base: Path = OUT_DIR) -> Path:
    """outputs: name -> events, e.g. rejected, duplicates, not_for_youth, needs_review."""
    run_dir = base / "staging" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    for name, events in outputs.items():
        _write_json(run_dir / f"{name}.json", events)
    _write_json(run_dir / "report.json", report)
    if not report["halted"]:
        write_outputs(run_dir, accepted, allowed, now)
        (run_dir / "READY_FOR_APPROVAL").write_text(now.isoformat(), encoding="utf-8")
    return run_dir


def latest_ready_run(base: Path = OUT_DIR) -> Path | None:
    staging = base / "staging"
    if not staging.exists():
        return None
    ready = sorted(p for p in staging.iterdir() if (p / "READY_FOR_APPROVAL").exists())
    return ready[-1] if ready else None


def merge_published(old: list[dict], new: list[dict], now: datetime) -> list[dict]:
    """All approved events, newest run first: the same event (same id, or same
    title + date + venue) from an older run is replaced by the newer version.
    Events that started before today are dropped."""
    today = now.astimezone(OSLO).date()
    merged, seen_ids, seen_keys = [], set(), set()
    for ev in new + old:
        if ev["id"] in seen_ids or dedupe_key(ev) in seen_keys:
            continue
        try:
            if datetime.fromisoformat(ev["start"]).astimezone(OSLO).date() < today:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        seen_ids.add(ev["id"])
        seen_keys.add(dedupe_key(ev))
        merged.append(ev)
    return sorted(merged, key=lambda e: e["start"])


def approve(run_dir: Path, base: Path = OUT_DIR, now: datetime | None = None) -> Path:
    """Add an approved run to out/public/ (earlier approved events stay)."""
    if not (run_dir / "READY_FOR_APPROVAL").exists():
        raise RuntimeError(f"{run_dir.name} is not ready for approval (halted or incomplete)")
    now = now or datetime.now(OSLO)
    public = base / "public"

    def _load(path: Path, default):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default

    old = _load(public / "events.json", [])
    previous = _load(public / "published.json", {})
    new = _load(run_dir / "events.json", [])
    events = merge_published(old if isinstance(old, list) else [], new, now)
    # A run staged before an event was unpublished must not bring it back.
    blocked = load_blocked(base)
    events = [e for e in events if not is_blocked(e, blocked)]
    allowed = sorted(f.stem for f in (run_dir / "feeds").glob("*.ics") if f.stem != "all")

    approved_at = now.isoformat(timespec="seconds")
    previous = previous if isinstance(previous, dict) else {}
    _replace_public(base, events, allowed, now, {
        **previous,
        "run_id": run_dir.name,
        "approved_at": approved_at,
        "runs": previous.get("runs", []) + [{"run_id": run_dir.name, "approved_at": approved_at,
                                             "events_in_run": len(new)}],
        "events_published": len(events),
    })
    (run_dir / "READY_FOR_APPROVAL").rename(run_dir / "APPROVED")
    return public


def _replace_public(base: Path, events: list[dict], allowed: list[str], now: datetime, info: dict) -> None:
    """Build the new public folder next to the old one, then swap, so the page
    never sees a half-written folder."""
    public, tmp = base / "public", base / "public.new"
    if tmp.exists():
        shutil.rmtree(tmp)
    write_outputs(tmp, events, allowed, now)
    _write_json(tmp / "published.json", info)
    if public.exists():
        shutil.rmtree(public)
    tmp.rename(public)


# ---------------------------------------------------------------- unpublish + block list
#
# A human can take one published event down again (`python -m harness unpublish`).
# The event is also put on a block list (out/blocked.json), so later runs and
# approvals don't publish it again: the pipeline rejects it with the reason
# UNPUBLISHED, and approve() filters it out of runs staged before the unpublish.

UNPUBLISHED = "unpublished_by_human"


def _blocked_path(base: Path) -> Path:
    return base / "blocked.json"


def load_blocked(base: Path = OUT_DIR) -> list[dict]:
    try:
        data = json.loads(_blocked_path(base).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def is_blocked(ev: dict, blocked: list[dict]) -> bool:
    """Same id, or same title + date + venue as a blocked event (so a copy of
    it with a new id, e.g. sent in again, is caught too)."""
    key = list(dedupe_key(ev))
    return any(b.get("id") == ev.get("id") or b.get("key") == key for b in blocked)


def published_events(base: Path = OUT_DIR) -> list[dict]:
    try:
        data = json.loads((base / "public" / "events.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def unpublish(event_id: str, base: Path = OUT_DIR, now: datetime | None = None, reason: str = "") -> dict:
    """Remove one event from out/public/, rebuild feeds and digest, and block it
    from being published again. Returns the removed event."""

    public = base / "public"
    if not (public / "published.json").exists():
        raise RuntimeError("Nothing is published yet.")
    events = published_events(base)
    match = [e for e in events if e.get("id") == event_id]
    if not match:
        raise ValueError(f"{event_id} is not among the published events")
    removed = match[0]
    now = now or datetime.now(OSLO)
    at = now.isoformat(timespec="seconds")
    reason = strip_pii(reason.strip())[0]  # free text: keep contact details out of the log

    entry = {"id": removed["id"], "key": list(dedupe_key(removed)), "title": removed.get("title", ""),
             "start": removed.get("start", ""), "venue_name": removed.get("venue_name", ""),
             "unpublished_at": at, "reason": reason}
    blocked = load_blocked(base)
    _blocked_path(base).parent.mkdir(parents=True, exist_ok=True)
    _write_json(_blocked_path(base), blocked + [entry])

    remaining = [e for e in events if e.get("id") != event_id]
    allowed = sorted(f.stem for f in (public / "feeds").glob("*.ics") if f.stem != "all")
    info = json.loads((public / "published.json").read_text(encoding="utf-8"))
    info = info if isinstance(info, dict) else {}
    _replace_public(base, remaining, allowed, now, {
        **info,
        "events_published": len(remaining),
        "unpublished": info.get("unpublished", []) + [
            {"id": removed["id"], "title": removed.get("title", ""), "at": at, "reason": reason}],
    })
    return removed


# ---------------------------------------------------------------- human review of the needs-review queue

REVIEW_ACTIONS = {"accept", "not_youth", "drop"}


def apply_review(run_dir: Path, decisions: dict[str, tuple], allowed: set[str]) -> dict:
    """Apply a reviewer's decisions to the needs-review queue of a staged run.

    decisions: event id -> ("accept", [categories]) | ("not_youth",) | ("drop",).
    Events without a decision stay in needs_review.json. Feeds and digest are
    rebuilt, so the run can then be approved as usual.
    """
    if not (run_dir / "READY_FOR_APPROVAL").exists():
        raise RuntimeError(f"{run_dir.name} is not waiting for approval (halted, incomplete or already approved)")

    def load(name):
        path = run_dir / f"{name}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    accepted, review, not_youth, rejected = load("events"), load("needs_review"), load("not_for_youth"), load("rejected")
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    review_ids = {e["id"] for e in review}

    for ev_id, decision in decisions.items():
        if ev_id not in review_ids:
            raise ValueError(f"{ev_id} is not in the needs-review queue")
        if not decision or decision[0] not in REVIEW_ACTIONS:
            raise ValueError(f"{ev_id}: decision must be one of {sorted(REVIEW_ACTIONS)}")
        if decision[0] == "accept":
            cats = list(decision[1]) if len(decision) > 1 else []
            unknown = [c for c in cats if c not in allowed]
            if not 1 <= len(cats) <= 3 or unknown:
                raise ValueError(f"{ev_id}: accept needs 1–3 categories from {sorted(allowed)}, got {cats}")

    now_iso = datetime.now(OSLO).isoformat(timespec="seconds")
    still_waiting, log = [], []
    for ev in review:
        decision = decisions.get(ev["id"])
        if not decision:
            still_waiting.append(ev)
            continue
        base = {k: v for k, v in ev.items() if k != "reasons"}
        action = decision[0]
        if action == "accept":
            accepted.append({**base, "categories": list(decision[1]), "youth": "yes",
                             "flags": base.get("flags", []) + ["accepted_in_review"]})
        elif action == "not_youth":
            not_youth.append({**base, "youth": "no", "flags": base.get("flags", []) + ["not_youth_in_review"]})
        else:
            rejected.append({**base, "reasons": ["dropped_in_review"]})
        log.append({"id": ev["id"], "decision": action, "at": now_iso})

    accepted.sort(key=lambda e: e["start"])
    run_time = datetime.fromisoformat(report["run_time"])
    write_outputs(run_dir, accepted, sorted(allowed), run_time)  # rewrites events.json, feeds, digest
    _write_json(run_dir / "needs_review.json", still_waiting)
    _write_json(run_dir / "not_for_youth.json", not_youth)
    _write_json(run_dir / "rejected.json", rejected)
    report["counts"].update(accepted=len(accepted), needs_review=len(still_waiting),
                            not_for_youth=len(not_youth), rejected=len(rejected))
    report.setdefault("review", []).extend(log)
    _write_json(run_dir / "report.json", report)
    return {"accepted": sum(d["decision"] == "accept" for d in log),
            "not_youth": sum(d["decision"] == "not_youth" for d in log),
            "dropped": sum(d["decision"] == "drop" for d in log),
            "still_waiting": len(still_waiting)}
