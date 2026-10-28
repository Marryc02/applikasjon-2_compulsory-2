"""Stage 2 (normalize): convert source records to the internal event format
described in context/event_schema.md."""
from __future__ import annotations

from datetime import datetime, time

from .config import OSLO
from .privacy import strip_pii

MAX_DESCRIPTION = 300


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _start_iso(start: dict) -> str:
    """Prefer the exact UTC dateTime; else combine localDate + localTime as Oslo time."""
    if start.get("dateTime"):
        dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        return dt.astimezone(OSLO).isoformat()
    if start.get("localDate"):
        d = datetime.fromisoformat(start["localDate"]).date()
        t = time.fromisoformat(start["localTime"]) if start.get("localTime") else time(0, 0)
        return datetime.combine(d, t, tzinfo=OSLO).isoformat()
    return ""


def normalize_ticketmaster(ev: dict) -> dict:
    dates = ev.get("dates", {})
    start = dates.get("start", {})
    venues = ev.get("_embedded", {}).get("venues", [])
    venue = venues[0] if venues else {}
    loc = venue.get("location", {})
    prices = ev.get("priceRanges") or [{}]

    source_categories = []
    for c in ev.get("classifications", []):
        for key in ("segment", "genre", "subGenre"):
            name = (c.get(key) or {}).get("name")
            if name and name != "Undefined" and name not in source_categories:
                source_categories.append(name)

    raw_desc = " ".join(x for x in (ev.get("info"), ev.get("pleaseNote")) if x).strip()
    description, pii_removed = strip_pii(raw_desc)
    if len(description) > MAX_DESCRIPTION:
        description = description[: MAX_DESCRIPTION - 1].rstrip() + "…"

    record = {
        "id": f"tm:{ev.get('id', '')}",
        "source": "ticketmaster",
        "source_url": ev.get("url", ""),
        "title": (ev.get("name") or "").strip(),
        "start": _start_iso(start),
        "date_tbd": bool(start.get("dateTBD") or start.get("dateTBA"))
        or not (start.get("dateTime") or start.get("localDate")),
        "status": (dates.get("status") or {}).get("code", ""),
        "venue_name": (venue.get("name") or "").strip(),
        "address": ((venue.get("address") or {}).get("line1") or "").strip(),
        "city": ((venue.get("city") or {}).get("name") or "").strip(),
        "lat": _to_float(loc.get("latitude")),
        "lon": _to_float(loc.get("longitude")),
        "price_min": _to_float(prices[0].get("min")),
        "price_max": _to_float(prices[0].get("max")),
        "currency": prices[0].get("currency"),
        "age_restricted": bool((ev.get("ageRestrictions") or {}).get("legalAgeEnforced")),
        "source_categories": source_categories,
        "description": description,
        "categories": [],
        "flags": ["pii_removed"] if pii_removed else [],
    }
    return record
