"""Event sources. Each source returns raw records; `kulturnett.normalize`
turns a record into the internal event format (harness/context/event_schema.md)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class SourceUnavailable(RuntimeError):
    pass


class SourceFormatError(SourceUnavailable):
    """The source answered, but with data the pipeline cannot read at all
    (stress test 2, repair R1). Nothing is staged."""


def load_file(path: Path) -> list:
    """Load saved records: a JSON list, or an object with an `events` list.
    Raises SourceFormatError with a plain explanation if the data is unreadable."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SourceFormatError(
            f"The source sent data that isn't valid JSON (it breaks off at line {e.lineno}, "
            f"column {e.colno}); the download may have been cut off. Nothing was staged.") from None
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        raise SourceFormatError(f"The source sent a {type(data).__name__} instead of a list of events. "
                                "Nothing was staged.")
    if "events" not in data:
        keys = [k for k in data if not str(k).startswith("_")]
        raise SourceFormatError(
            f"The source's data has no 'events' list (found: {', '.join(keys) or 'nothing'}). "
            "The source may have changed its format. Nothing was staged.")
    if not isinstance(data["events"], list):
        raise SourceFormatError("The source's 'events' is not a list. The source may have changed its format. "
                                "Nothing was staged.")
    return data["events"]


def file_run_time(path: Path) -> str | None:
    """The run time a saved file was made for (`"_run_time"`), if it has one.
    Its event dates are fixed, so replaying it at today's date would reject them as past."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None  # load_file reports the problem when the run starts
    value = data.get("_run_time") if isinstance(data, dict) else None
    return value if isinstance(value, str) else None


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
