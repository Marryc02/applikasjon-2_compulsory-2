"""User-facing output shows Norwegian category names, never the English IDs."""
from datetime import datetime

from harness.classify import load_categories
from harness.config import OSLO
from harness.labels import LABELS_NO, label
from harness.publish import write_outputs

NOW = datetime(2026, 11, 2, 8, 0, tzinfo=OSLO)
ALLOWED = sorted(load_categories()[0])


def _event(cats):
    return {"id": "test:1", "source": "test", "source_url": "https://example.org/1",
            "title": "Kurs", "start": "2026-11-03T19:00:00+01:00", "all_day": False,
            "status": "active", "venue_name": "Biblioteket", "kommune": "Hamar",
            "categories": cats, "youth": "yes", "flags": []}


def test_every_category_has_a_norwegian_label():
    assert set(ALLOWED) <= set(LABELS_NO), "add the new category to harness/labels.py"


def test_feeds_and_digest_use_norwegian_names(tmp_path):
    write_outputs(tmp_path, [_event(["learning", "arts_culture"])], ALLOWED, NOW)
    feed = (tmp_path / "feeds" / "learning.ics").read_text(encoding="utf-8")
    assert "X-WR-CALNAME:Unge i Hamar – Læring" in feed
    assert "CATEGORIES:Læring,Kunst og kultur" in feed
    for cat in ALLOWED:
        text = (tmp_path / "feeds" / f"{cat}.ics").read_text(encoding="utf-8")
        assert f"X-WR-CALNAME:Unge i Hamar – {label(cat)}" in text
    digest = (tmp_path / "digest.md").read_text(encoding="utf-8")
    assert "(Læring, Kunst og kultur)" in digest and "learning" not in digest
