"""Kulturnett Innlandet ("Hva skjer") source.

STATUS: API access requested, not granted yet. The record format is ASSUMED,
see harness/context/kulturnett_format.md. When the real format is known, only
this file should need to change.
"""
from __future__ import annotations

from datetime import date, datetime, time

from ..config import OSLO
from ..privacy import strip_pii
from . import SourceUnavailable

MAX_DESCRIPTION = 300
STATUS_MAP = {"publisert": "active", "avlyst": "cancelled", "utsatt": "postponed"}


def fetch_live(cfg: dict, now: datetime) -> list[dict]:
    raise SourceUnavailable(
        "Kulturnett Innlandet API access has not been granted yet. "
        "Use --source synthetic, or --offline <file> to replay saved data."
    )


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_start(value: str | None, all_day: bool) -> str:
    """Return ISO 8601 in Oslo time, or '' if missing/unparseable."""
    if not value:
        return ""
    try:
        if all_day or len(value) == 10:
            d = date.fromisoformat(value[:10])
            return datetime.combine(d, time(0, 0), tzinfo=OSLO).isoformat()
        dt = datetime.fromisoformat(value)
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=OSLO)
    return dt.astimezone(OSLO).isoformat()


def normalize(rec: dict) -> dict:
    """Convert one (assumed-format) Kulturnett record to the internal format.
    Keys starting with '_' (test labels) are never copied."""
    sted = rec.get("sted") or {}
    all_day = bool(rec.get("heldags")) or (isinstance(rec.get("start"), str) and len(rec["start"]) == 10)

    description, pii_removed = strip_pii((rec.get("beskrivelse") or "").strip())
    if len(description) > MAX_DESCRIPTION:
        description = description[: MAX_DESCRIPTION - 1].rstrip() + "…"

    raw_status = (rec.get("status") or "").strip().lower()
    return {
        "id": f"kn:{rec.get('id', '')}" if rec.get("id") else "",
        "source": "kulturnett",
        "source_url": (rec.get("url") or "").strip(),
        "title": (rec.get("tittel") or "").strip(),
        "start": _parse_start(rec.get("start"), all_day),
        "all_day": all_day,
        "status": STATUS_MAP.get(raw_status, raw_status or "unknown"),
        "venue_name": (sted.get("navn") or "").strip(),
        "address": (sted.get("adresse") or "").strip(),
        "kommune": (sted.get("kommune") or "").strip(),
        "lat": _to_float(sted.get("lat")),
        "lon": _to_float(sted.get("lon")),
        "organizer": (rec.get("arrangor") or "").strip(),
        "price": (rec.get("pris") or "").strip(),
        "source_categories": [c for c in rec.get("kategorier") or [] if isinstance(c, str)],
        "description": description,
        "categories": [],
        "youth": "",
        "flags": ["pii_removed"] if pii_removed else [],
    }
