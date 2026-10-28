"""Stage 4 (dedupe): drop events with the same normalized title, date and venue."""
from __future__ import annotations

import re
import unicodedata


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").casefold()
    return re.sub(r"[\W_]+", " ", text).strip()


def dedupe_key(ev: dict) -> tuple[str, str, str]:
    return (_norm(ev.get("title", "")), (ev.get("start") or "")[:10], _norm(ev.get("venue_name", "")))


def dedupe(events: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (unique events, duplicates). Each duplicate gets 'duplicate_of'."""
    seen: dict[tuple, str] = {}
    seen_ids: set[str] = set()
    unique, dupes = [], []
    for ev in events:
        key = dedupe_key(ev)
        if ev["id"] in seen_ids:
            dupes.append({**ev, "duplicate_of": ev["id"]})
        elif key in seen:
            dupes.append({**ev, "duplicate_of": seen[key]})
        else:
            seen[key] = ev["id"]
            seen_ids.add(ev["id"])
            unique.append(ev)
    return unique, dupes
