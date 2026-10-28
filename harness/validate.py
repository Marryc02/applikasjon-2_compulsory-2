"""Stage 3 (validate): mechanical checks on normalized events. Pure code, no LLM.
Rules are documented in context/event_schema.md."""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlparse

from .geo import haversine_km

REQUIRED = ("id", "title", "start", "venue_name", "city", "source_url")
ACTIVE_STATUSES = {"onsale", "offsale", "rescheduled"}


def validate_event(ev: dict, cfg: dict, now: datetime) -> list[str]:
    """Return a list of rejection reasons. Empty list = valid."""
    reasons = [f"missing_field:{f}" for f in REQUIRED if not ev.get(f)]

    url = ev.get("source_url") or ""
    if url:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            reasons.append("invalid_url")

    if ev.get("status") not in ACTIVE_STATUSES:
        reasons.append("status_not_active")

    if ev.get("date_tbd"):
        reasons.append("date_tbd")

    if ev.get("start"):
        try:
            start = datetime.fromisoformat(ev["start"])
        except ValueError:
            reasons.append("invalid_start")
        else:
            if start < now:
                reasons.append("in_past")
            elif start > now + timedelta(days=cfg["window"]["days_ahead"]):
                reasons.append("too_far_ahead")

    area = cfg["area"]
    if ev.get("lat") is not None and ev.get("lon") is not None:
        dist = haversine_km(area["center_lat"], area["center_lon"], ev["lat"], ev["lon"])
        if dist > area["radius_km"]:
            reasons.append("outside_area")
    elif ev.get("city") and ev["city"] not in area["allowed_cities"]:
        reasons.append("outside_area")

    return reasons


def validate_categories(ev: dict, allowed: set[str]) -> list[str]:
    cats = ev.get("categories") or []
    reasons = []
    if not cats:
        reasons.append("no_category")
    unknown = [c for c in cats if c not in allowed]
    if unknown:
        reasons.append("unknown_category:" + ",".join(unknown))
    if len(cats) > 3:
        reasons.append("too_many_categories")
    return reasons
