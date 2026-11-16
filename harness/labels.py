"""Norwegian display names for category IDs.

The category IDs themselves are defined only in harness/context/categories.md.
This file only says how each ID is shown to users (web page, feed names,
event files, digest). A new category without a label here is shown by its ID,
and a test fails until it gets one.
"""
from __future__ import annotations

LABELS_NO = {
    "music": "Musikk",
    "sports": "Sport",
    "gaming": "Spill",
    "arts_culture": "Kunst og kultur",
    "film": "Film",
    "outdoors": "Friluftsliv",
    "food": "Mat",
    "learning": "Læring",
    "social": "Sosialt",
}


def label(cat: str) -> str:
    return LABELS_NO.get(cat, cat)
