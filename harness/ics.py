"""Write iCalendar (.ics) feeds by hand (RFC 5545), no dependencies."""
from __future__ import annotations

from datetime import datetime, timezone


def _escape(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Fold lines longer than 75 octets, as RFC 5545 requires."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, current = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        limit = 75 if not parts else 74  # continuation lines start with a space
        if len(current) + len(b) > limit:
            parts.append(current.decode("utf-8"))
            current = b""
        current += b
    parts.append(current.decode("utf-8"))
    return "\r\n ".join(parts)


def _utc(dt_iso: str) -> str:
    return datetime.fromisoformat(dt_iso).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _dtstart(ev: dict) -> str:
    if ev.get("all_day"):
        return f"DTSTART;VALUE=DATE:{datetime.fromisoformat(ev['start']):%Y%m%d}"
    return f"DTSTART:{_utc(ev['start'])}"


def build_calendar(events: list[dict], name: str, stamp: datetime) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//hamar-youth-events//NO",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escape(name)}",
        "X-WR-TIMEZONE:Europe/Oslo",
    ]
    dtstamp = stamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for ev in events:
        location = ", ".join(x for x in (ev.get("venue_name"), ev.get("address"), ev.get("kommune")) if x)
        desc = ev.get("description") or ""
        desc = f"{desc}\n\nKilde: {ev['source_url']}".strip()
        lines += [
            "BEGIN:VEVENT",
            f"UID:{ev['id']}@hamar-youth-events",
            f"DTSTAMP:{dtstamp}",
            _dtstart(ev),
            f"SUMMARY:{_escape(ev['title'])}",
            f"LOCATION:{_escape(location)}",
            f"URL:{ev['source_url']}",
            f"DESCRIPTION:{_escape(desc)}",
            f"CATEGORIES:{','.join(ev.get('categories', []))}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"
