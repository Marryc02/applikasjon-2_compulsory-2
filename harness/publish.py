"""Stage 6 (stage) and stage 7 (publish after human approval).

The pipeline never publishes by itself. It writes a run to out/staging/<run_id>/.
A person reviews it and runs `python -m harness approve`, which copies it to
out/public/.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from .config import OUT_DIR, OSLO
from .ics import build_calendar

DAYS_NO = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
MONTHS_NO = ["januar", "februar", "mars", "april", "mai", "juni", "juli",
             "august", "september", "oktober", "november", "desember"]


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_digest(events: list[dict], now: datetime) -> str:
    """Weekly digest in Norwegian: events in the next 7 days, grouped by day."""
    end = now + timedelta(days=7)
    week = sorted(
        (e for e in events if now <= datetime.fromisoformat(e["start"]) < end),
        key=lambda e: e["start"],
    )
    out = [f"# Denne uka for unge i Hamar", "",
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
        out.append(f"- **{start:%H:%M}** [{e['title']}]({e['source_url']}), {e['venue_name']} ({cats})")
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


def stage_run(run_id: str, accepted, rejected, duplicates, needs_review, report, allowed, now,
              base: Path = OUT_DIR) -> Path:
    run_dir = base / "staging" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "rejected.json", rejected)
    _write_json(run_dir / "duplicates.json", duplicates)
    _write_json(run_dir / "needs_review.json", needs_review)
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


def approve(run_dir: Path, base: Path = OUT_DIR) -> Path:
    if not (run_dir / "READY_FOR_APPROVAL").exists():
        raise RuntimeError(f"{run_dir.name} is not ready for approval (halted or incomplete)")
    public = base / "public"
    if public.exists():
        shutil.rmtree(public)
    public.mkdir(parents=True)
    shutil.copy2(run_dir / "events.json", public / "events.json")
    shutil.copy2(run_dir / "digest.md", public / "digest.md")
    shutil.copytree(run_dir / "feeds", public / "feeds")
    _write_json(public / "published.json", {
        "run_id": run_dir.name,
        "approved_at": datetime.now(OSLO).isoformat(timespec="seconds"),
    })
    (run_dir / "READY_FOR_APPROVAL").rename(run_dir / "APPROVED")
    return public
