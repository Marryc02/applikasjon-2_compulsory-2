"""Stage 1 (collect): fetch upcoming events near Hamar from the Ticketmaster
Discovery API, or load a saved response file in offline mode."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .geo import geohash

API_URL = "https://app.ticketmaster.com/discovery/v2/events.json"


class FetchError(RuntimeError):
    pass


def _utc_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_json(url: str, timeout: float, max_retries: int) -> dict:
    """GET with retries on rate limiting (429) and server errors (5xx)."""
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            retryable = e.code == 429 or e.code >= 500
            if not retryable or attempt == max_retries:
                # Never include the URL: it contains the API key.
                raise FetchError(f"Ticketmaster HTTP {e.code} (attempt {attempt})") from None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == max_retries:
                raise FetchError(f"Ticketmaster unreachable: {type(e).__name__}") from None
        time.sleep(2 ** attempt)
    raise FetchError("unreachable")  # pragma: no cover


def fetch_live(cfg: dict, now: datetime, api_key: str) -> list[dict]:
    tm, area = cfg["ticketmaster"], cfg["area"]
    params = {
        "apikey": api_key,
        "geoPoint": geohash(area["center_lat"], area["center_lon"], 9),
        "radius": str(area["radius_km"]),
        "unit": "km",
        "countryCode": tm["country_code"],
        "startDateTime": _utc_z(now),
        "endDateTime": _utc_z(now + timedelta(days=cfg["window"]["days_ahead"])),
        "size": str(tm["page_size"]),
        "sort": "date,asc",
    }
    events: list[dict] = []
    page = 0
    while len(events) < tm["max_events"]:
        params["page"] = str(page)
        url = f"{API_URL}?{urllib.parse.urlencode(params)}"
        data = _get_json(url, tm["request_timeout_s"], tm["max_retries"])
        batch = data.get("_embedded", {}).get("events", [])
        events.extend(batch)
        total_pages = data.get("page", {}).get("totalPages", 1)
        page += 1
        if not batch or page >= total_pages:
            break
        time.sleep(0.25)  # stay well under the API's rate limit
    return events[: tm["max_events"]]


def load_offline(path: Path) -> list[dict]:
    """Load a saved Ticketmaster response (same shape as the live API)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("_embedded", {}).get("events", [])
