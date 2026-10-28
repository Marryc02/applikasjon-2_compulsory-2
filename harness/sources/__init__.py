"""Event sources. Each source returns raw records; `kulturnett.normalize`
turns a record into the internal event format (harness/context/event_schema.md)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class SourceUnavailable(RuntimeError):
    pass


def load_file(path: Path) -> list[dict]:
    """Load saved records: a JSON list, or an object with an `events` list."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("events", [])


def collect(source: str, cfg: dict, now: datetime, offline_file: Path | None = None) -> tuple[list[dict], str]:
    """Return (raw records, description of where they came from)."""
    if offline_file:
        return load_file(offline_file), f"file:{Path(offline_file).name}"
    if source == "synthetic":
        from .synthetic import generate
        return generate(now), "synthetic (simulated Kulturnett feed)"
    if source == "kulturnett":
        from .kulturnett import fetch_live
        return fetch_live(cfg, now), "kulturnett:live"
    raise SourceUnavailable(f"Unknown source: {source}")
