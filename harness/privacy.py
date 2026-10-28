"""Remove personal contact data (emails, Norwegian phone numbers) from free text."""
from __future__ import annotations

import re

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# +47 optional, then 8 digits written as 12345678, 123 45 678 or 12 34 56 78.
# Not part of a longer number or a date like 05.11.2026 (a full stop that ends
# the sentence is fine).
PHONE_RE = re.compile(
    r"(?<!\d)(?<!\d[.\-/])(?:\+47[\s-]?)?(?:\d{8}|\d{3}\s\d{2}\s\d{3}|\d{2}\s\d{2}\s\d{2}\s\d{2})(?!\d|[.\-/]\d)"
)
# Known limitation: personal NAMES are not detected by these patterns.


def strip_pii(text: str) -> tuple[str, bool]:
    """Return (cleaned text, whether anything was removed)."""
    if not text:
        return text, False
    cleaned = EMAIL_RE.sub("[fjernet]", text)
    cleaned = PHONE_RE.sub("[fjernet]", cleaned)
    return cleaned, cleaned != text
