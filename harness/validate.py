"""Stage 3 (validate): mechanical checks on normalized events. Pure code, no LLM.
Rules are documented in harness/context/event_schema.md."""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlparse

REQUIRED = ("id", "title", "start", "venue_name", "kommune", "source_url")


def validate_event(ev: dict, cfg: dict, now: datetime) -> list[str]:
    """Return a list of rejection reasons. Empty list = valid."""
    reasons = [f"missing_field:{f}" for f in REQUIRED if not ev.get(f)]

    url = ev.get("source_url") or ""
    if url:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            reasons.append("invalid_url")

    if ev.get("status") != "active":
        reasons.append("status_not_active")

    if ev.get("start"):
        try:
            start = datetime.fromisoformat(ev["start"])
        except ValueError:
            reasons.append("invalid_start")
        else:
            # An all-day event today is still upcoming.
            cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0) if ev.get("all_day") else now
            if start < cutoff:
                reasons.append("in_past")
            elif start > now + timedelta(days=cfg["window"]["days_ahead"]):
                reasons.append("too_far_ahead")

    if ev.get("kommune") and ev["kommune"] not in cfg["area"]["kommuner"]:
        reasons.append("outside_area")

    return reasons


def validate_classification(ev: dict, allowed: set[str]) -> list[str]:
    """Problems that send an event to human review instead of publishing."""
    cats = ev.get("categories") or []
    reasons = []
    if ev.get("youth") == "unsure":
        reasons.append("youth_unsure")
    if not cats:
        reasons.append("no_category")
    unknown = [c for c in cats if c not in allowed]
    if unknown:
        reasons.append("unknown_category:" + ",".join(unknown))
    if len(cats) > 3:
        reasons.append("too_many_categories")
    return reasons
