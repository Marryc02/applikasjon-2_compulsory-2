"""Public, read-only web page for approved youth events (T11).

Reads only `out/public/`, which only `python -m harness approve` writes to.
Never reads `out/staging/`, never writes anything, no accounts, no cookies.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, abort, render_template, request, send_from_directory

from harness.classify import load_categories
from harness.config import OSLO, OUT_DIR, load_config
from harness.ics import build_calendar
from harness.labels import label
from harness.privacy import strip_pii
from harness.publish import DAYS_NO, MONTHS_NO


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _upcoming(events: list[dict], now: datetime) -> list[dict]:
    """Events that have not started yet (all-day events: not before today)."""
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    for ev in events:
        try:
            start = datetime.fromisoformat(ev["start"]).astimezone(OSLO)
        except (KeyError, TypeError, ValueError):
            continue
        if start >= (today if ev.get("all_day") else now):
            out.append({**ev, "_start": start})
    return sorted(out, key=lambda e: e["_start"])


def _filename(title: str) -> str:
    """ASCII file name for a downloaded event, e.g. "Konsert på Kulturhuset" -> "konsert-pa-kulturhuset.ics"."""
    text = (title or "").lower().translate(str.maketrans({"æ": "ae", "ø": "o", "å": "a"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60].strip("-")
    return f"{slug or 'arrangement'}.ics"


def _view(ev: dict) -> dict:
    """Only the fields the page shows. Free text is scrubbed again as a safety net."""
    start = ev["_start"]
    url = ev.get("source_url") or ""
    return {
        "id": ev.get("id") or "",
        "title": ev.get("title", ""),
        "time": "Hele dagen" if ev.get("all_day") else f"{start:%H:%M}",
        "venue": ev.get("venue_name", ""),
        "kommune": ev.get("kommune", ""),
        "price": ev.get("price") or "",
        "description": strip_pii(ev.get("description") or "")[0],
        "url": url if url.startswith("https://") else "",
        "categories": [(c, label(c)) for c in ev.get("categories", [])],
    }


def _group_by_day(events: list[dict]) -> list[tuple[str, list[dict]]]:
    days: list[tuple[str, list[dict]]] = []
    current = None
    for ev in events:
        start = ev["_start"]
        if start.date() != current:
            current = start.date()
            heading = f"{DAYS_NO[start.weekday()].capitalize()} {start.day}. {MONTHS_NO[start.month - 1]}"
            days.append((heading, []))
        days[-1][1].append(_view(ev))
    return days


def create_app(public_dir: Path | None = None,
               now_fn: Callable[[], datetime] = lambda: datetime.now(OSLO),
               kommuner: list[str] | None = None) -> Flask:
    public_dir = Path(public_dir or OUT_DIR / "public")
    # The area filter uses the same list as validation (config.toml [area]).
    kommuner = list(kommuner if kommuner is not None else load_config()["area"]["kommuner"])
    app = Flask(__name__)

    def categories() -> list[str]:
        allowed, _ = load_categories()
        return sorted(allowed, key=label)

    @app.get("/")
    def index():
        cats = categories()
        chosen = request.args.get("kategori", "")
        if chosen not in cats:
            chosen = ""
        place = request.args.get("kommune", "")
        if place not in kommuner:
            place = ""
        published = _read_json(public_dir / "published.json", None)
        events = _read_json(public_dir / "events.json", []) if published else []
        upcoming = _upcoming(events if isinstance(events, list) else [], now_fn())
        if chosen:
            upcoming = [e for e in upcoming if chosen in e.get("categories", [])]
        if place:
            upcoming = [e for e in upcoming if e.get("kommune") == place]
        updated = ""
        if published and published.get("approved_at"):
            try:
                at = datetime.fromisoformat(published["approved_at"]).astimezone(OSLO)
                updated = f"{at.day}. {MONTHS_NO[at.month - 1]} {at.year}"
            except ValueError:
                pass
        return render_template(
            "index.html",
            published=bool(published),
            days=_group_by_day(upcoming),
            categories=[(c, label(c)) for c in cats],
            chosen=chosen,
            chosen_label=label(chosen) if chosen else "",
            kommuner=kommuner,
            place=place,
            updated=updated,
        )

    @app.get("/feeds/<name>.ics")
    def feed(name: str):
        if name != "all" and name not in categories():
            abort(404)
        if not (public_dir / "published.json").exists():
            abort(404)
        return send_from_directory(public_dir / "feeds", f"{name}.ics",
                                   mimetype="text/calendar", max_age=300)

    @app.get("/arrangement/<path:event_id>.ics")
    def event_ics(event_id: str):
        """One upcoming, approved event as a downloadable .ics file ("Legg i kalender")."""
        if not (public_dir / "published.json").exists():
            abort(404)
        events = _read_json(public_dir / "events.json", [])
        upcoming = _upcoming(events if isinstance(events, list) else [], now_fn())
        match = next((e for e in upcoming if e.get("id") and e["id"] == event_id), None)
        if match is None:
            abort(404)
        ev = {k: v for k, v in match.items() if k != "_start"}
        ev["description"] = strip_pii(ev.get("description") or "")[0]
        body = build_calendar([ev], ev.get("title") or "Arrangement", now_fn())
        resp = Response(body, mimetype="text/calendar")
        resp.headers["Content-Disposition"] = f'attachment; filename="{_filename(ev.get("title", ""))}"'
        return resp

    @app.after_request
    def headers(resp):
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'self' 'unsafe-inline'"
        return resp

    return app
