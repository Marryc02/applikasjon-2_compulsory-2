"""Unit tests for the code-checked parts: privacy, validation, dedupe, parsing, ICS."""
from datetime import datetime

import pytest

from harness.classify import BaselineClassifier, load_categories, parse_llm_output
from harness.config import OSLO, load_config
from harness.dedupe import dedupe
from harness.ics import build_calendar
from harness.privacy import strip_pii
from harness.validate import validate_categories, validate_event

CFG = load_config()
NOW = datetime(2026, 11, 2, 8, 0, tzinfo=OSLO)
ALLOWED, _ = load_categories()


def good_event(**overrides):
    ev = {
        "id": "tm:X1", "source": "ticketmaster", "source_url": "https://www.ticketmaster.no/event/X1",
        "title": "Konsert", "start": "2026-11-05T19:00:00+01:00", "date_tbd": False, "status": "onsale",
        "venue_name": "Hamar kulturhus", "address": "Torggata 100", "city": "Hamar",
        "lat": 60.7949, "lon": 11.0669, "source_categories": ["Music"], "description": "",
        "categories": [], "flags": [],
    }
    ev.update(overrides)
    return ev


# ---------------------------------------------------------------- privacy

@pytest.mark.parametrize("text", [
    "Ring 912 34 567.", "Ring 91234567", "Ring +47 91 23 45 67 i dag", "mail: ola@example.no",
])
def test_pii_removed(text):
    cleaned, removed = strip_pii(text)
    assert removed and "[fjernet]" in cleaned


@pytest.mark.parametrize("text", [
    "Start kl. 17:00", "Dato 05.11.2026", "Pris 250 kr", "Postnummer 2317 Hamar", "13–19 år", "2026-11-05",
])
def test_pii_keeps_normal_text(text):
    assert strip_pii(text) == (text, False)


# ---------------------------------------------------------------- validation

def test_valid_event_passes():
    assert validate_event(good_event(), CFG, NOW) == []


@pytest.mark.parametrize("overrides, reason", [
    ({"title": ""}, "missing_field:title"),
    ({"venue_name": ""}, "missing_field:venue_name"),
    ({"source_url": "http://insecure.example"}, "invalid_url"),
    ({"status": "cancelled"}, "status_not_active"),
    ({"date_tbd": True}, "date_tbd"),
    ({"start": "2026-10-01T19:00:00+02:00"}, "in_past"),
    ({"start": "2027-06-01T19:00:00+02:00"}, "too_far_ahead"),
    ({"lat": 59.9127, "lon": 10.7461, "city": "Oslo"}, "outside_area"),
    ({"lat": None, "lon": None, "city": "Lillehammer"}, "outside_area"),
])
def test_rejections(overrides, reason):
    assert reason in validate_event(good_event(**overrides), CFG, NOW)


def test_city_fallback_accepts_allowed_city():
    assert validate_event(good_event(lat=None, lon=None, city="Ottestad"), CFG, NOW) == []


def test_category_validation():
    assert validate_categories({"categories": ["music"]}, ALLOWED) == []
    assert "no_category" in validate_categories({"categories": []}, ALLOWED)
    assert validate_categories({"categories": ["party"]}, ALLOWED)[0].startswith("unknown_category")


# ---------------------------------------------------------------- dedupe

def test_dedupe_same_title_different_case_and_punctuation():
    a = good_event(id="tm:A", title="Konsert: Ungdomsband")
    b = good_event(id="tm:B", title="KONSERT  ungdomsband!")
    c = good_event(id="tm:C", title="Konsert: Ungdomsband", start="2026-11-06T19:00:00+01:00")
    unique, dupes = dedupe([a, b, c])
    assert [e["id"] for e in unique] == ["tm:A", "tm:C"]
    assert dupes[0]["duplicate_of"] == "tm:A"


# ---------------------------------------------------------------- LLM output parsing

def test_parse_llm_output_ok():
    assert parse_llm_output('{"categories": ["music", "social"]}', ALLOWED) == ["music", "social"]
    assert parse_llm_output('```json\n{"categories": []}\n```', ALLOWED) == []


@pytest.mark.parametrize("bad", [
    "music", '{"cats": ["music"]}', '{"categories": ["party"]}',
    '{"categories": ["music","sports","film","food"]}', '{"categories": "music"}',
])
def test_parse_llm_output_rejects(bad):
    with pytest.raises(ValueError):
        parse_llm_output(bad, ALLOWED)


# ---------------------------------------------------------------- baseline classifier

@pytest.mark.parametrize("title, source_cats, expected", [
    ("LAN-party", ["Sports"], "gaming"),
    ("Quiz-kveld", [], "social"),
    ("Jazzkveld", ["Music"], "music"),
    ("Ishockey", ["Sports", "Ice Hockey"], "sports"),
])
def test_baseline(title, source_cats, expected):
    ev = good_event(title=title, source_categories=source_cats)
    assert expected in BaselineClassifier(ALLOWED).classify(ev)


# ---------------------------------------------------------------- ICS

def test_ics_structure_and_escaping():
    ev = good_event(title="Pizza, spill; moro", categories=["food", "gaming"],
                    description="Lang tekst " * 20)
    cal = build_calendar([ev], "Test", NOW)
    assert cal.startswith("BEGIN:VCALENDAR\r\n") and cal.endswith("END:VCALENDAR\r\n")
    assert "SUMMARY:Pizza\\, spill\\; moro" in cal
    assert "DTSTART:20261105T180000Z" in cal  # 19:00 Oslo = 18:00 UTC
    assert all(len(line.encode()) <= 75 for line in cal.split("\r\n"))


# ---------------------------------------------------------------- fallback when the LLM fails

from harness.classify import BudgetExceeded, classify_all


class FakeLLM:
    name = "llm"

    def __init__(self, behaviour):
        self.behaviour, self.calls, self.tokens = behaviour, 0, 0

    def classify(self, ev):
        self.calls += 1
        if self.behaviour == "error":
            raise ConnectionError("API down")
        if self.behaviour == "budget" and self.calls > 1:
            raise BudgetExceeded("max_llm_calls reached")
        return ["music"]


def test_llm_errors_fall_back_to_baseline():
    evs = [good_event(id=f"tm:{i}", title="Quiz-kveld", source_categories=[]) for i in range(3)]
    stats = classify_all(evs, FakeLLM("error"), BaselineClassifier(ALLOWED))
    assert stats["llm_errors"] == 3 and stats["fallback_used"] == 3
    assert all(e["categories"] == ["social"] and "classified_by_baseline" in e["flags"] for e in evs)


def test_budget_exhaustion_stops_llm_calls():
    evs = [good_event(id=f"tm:{i}", title="Quiz-kveld", source_categories=[]) for i in range(4)]
    llm = FakeLLM("budget")
    stats = classify_all(evs, llm, BaselineClassifier(ALLOWED))
    assert stats["budget_exhausted"] and llm.calls == 2  # no calls after the budget is hit
    assert evs[0]["categories"] == ["music"] and evs[3]["categories"] == ["social"]
