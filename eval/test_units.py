"""Unit tests for the code-checked parts: privacy, validation, dedupe, parsing, ICS."""
from datetime import datetime

import pytest

from harness.classify import BaselineClassifier, load_categories, parse_llm_output
from harness.config import OSLO, load_config
from harness.dedupe import dedupe
from harness.ics import build_calendar
from harness.privacy import strip_pii
from harness.validate import validate_classification, validate_event

CFG = load_config()
NOW = datetime(2026, 11, 2, 8, 0, tzinfo=OSLO)
ALLOWED, _ = load_categories()


def good_event(**overrides):
    ev = {
        "id": "kn:X1", "source": "kulturnett", "source_url": "https://synthetic.example/hva-skjer/X1",
        "title": "Konsert", "start": "2026-11-05T19:00:00+01:00", "all_day": False, "status": "active",
        "venue_name": "Hamar kulturhus", "address": "Torggata 100", "kommune": "Hamar",
        "lat": 60.7949, "lon": 11.0669, "organizer": "", "price": "", "source_categories": ["Konsert"],
        "description": "", "categories": [], "youth": "", "flags": [],
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
    ({"kommune": ""}, "missing_field:kommune"),
    ({"source_url": "http://insecure.example"}, "invalid_url"),
    ({"status": "cancelled"}, "status_not_active"),
    ({"status": "unknown"}, "status_not_active"),
    ({"start": "2026-10-01T19:00:00+02:00"}, "in_past"),
    ({"start": "2027-06-01T19:00:00+02:00"}, "too_far_ahead"),
    ({"start": "not a date"}, "invalid_start"),
    ({"kommune": "Lillehammer"}, "outside_area"),
])
def test_rejections(overrides, reason):
    assert reason in validate_event(good_event(**overrides), CFG, NOW)


@pytest.mark.parametrize("kommune", ["Hamar", "Løten", "Ringsaker", "Stange"])
def test_all_area_municipalities_accepted(kommune):
    assert validate_event(good_event(kommune=kommune), CFG, NOW) == []


def test_all_day_event_today_is_not_in_past():
    ev = good_event(start="2026-11-02T00:00:00+01:00", all_day=True)  # NOW is 08:00 the same day
    assert validate_event(ev, CFG, NOW) == []


def test_classification_validation():
    assert validate_classification({"categories": ["music"], "youth": "yes"}, ALLOWED) == []
    assert "no_category" in validate_classification({"categories": [], "youth": "yes"}, ALLOWED)
    assert "youth_unsure" in validate_classification({"categories": ["music"], "youth": "unsure"}, ALLOWED)
    assert validate_classification({"categories": ["party"], "youth": "yes"}, ALLOWED)[0].startswith("unknown_category")


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
    assert parse_llm_output('{"categories": ["music", "social"], "youth": "yes"}', ALLOWED) == \
        {"categories": ["music", "social"], "youth": "yes"}
    assert parse_llm_output('```json\n{"categories": [], "youth": "unsure"}\n```', ALLOWED) == \
        {"categories": [], "youth": "unsure"}


@pytest.mark.parametrize("bad", [
    "music", '{"cats": ["music"], "youth": "yes"}', '{"categories": ["party"], "youth": "yes"}',
    '{"categories": ["music","sports","film","food"], "youth": "yes"}', '{"categories": "music", "youth": "yes"}',
    '{"categories": ["music"]}', '{"categories": ["music"], "youth": "maybe"}', '["music"]',
])
def test_parse_llm_output_rejects(bad):
    with pytest.raises(ValueError):
        parse_llm_output(bad, ALLOWED)


# ---------------------------------------------------------------- baseline classifier

@pytest.mark.parametrize("title, source_cats, expected", [
    ("LAN-party", ["Idrett"], "gaming"),
    ("Quiz-kveld", [], "social"),
    ("Jazzkveld", ["Konsert"], "music"),
    ("Ishockey for nybegynnere", [], "sports"),
])
def test_baseline_categories(title, source_cats, expected):
    ev = good_event(title=title, source_categories=source_cats)
    assert expected in BaselineClassifier(ALLOWED).classify(ev)["categories"]


def test_baseline_does_not_match_lan_inside_words():
    ev = good_event(title="Planleggingsmøte", source_categories=[])
    assert "gaming" not in BaselineClassifier(ALLOWED).classify(ev)["categories"]


@pytest.mark.parametrize("title, source_cats, expected", [
    ("Konsert", ["Ungdom"], "yes"),
    ("Kveld for unge voksne", [], "yes"),
    ("Seniortreff", ["Ungdom"], "no"),   # explicit other audience wins
    ("Babysang", [], "no"),
    ("Kunstutstilling", [], "unsure"),
])
def test_baseline_youth(title, source_cats, expected):
    ev = good_event(title=title, source_categories=source_cats)
    assert BaselineClassifier(ALLOWED).classify(ev)["youth"] == expected


# ---------------------------------------------------------------- ICS

def test_ics_structure_and_escaping():
    ev = good_event(title="Pizza, spill; moro", categories=["food", "gaming"],
                    description="Lang tekst " * 20)
    cal = build_calendar([ev], "Test", NOW)
    assert cal.startswith("BEGIN:VCALENDAR\r\n") and cal.endswith("END:VCALENDAR\r\n")
    assert "SUMMARY:Pizza\\, spill\\; moro" in cal
    assert "DTSTART:20261105T180000Z" in cal  # 19:00 Oslo = 18:00 UTC
    assert all(len(line.encode()) <= 75 for line in cal.split("\r\n"))


def test_ics_all_day_uses_date_value():
    ev = good_event(start="2026-11-07T00:00:00+01:00", all_day=True, categories=["arts_culture"])
    assert "DTSTART;VALUE=DATE:20261107" in build_calendar([ev], "Test", NOW)


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
        return {"categories": ["music"], "youth": "yes"}


def test_llm_errors_fall_back_to_baseline():
    evs = [good_event(id=f"tm:{i}", title="Quiz-kveld", source_categories=[]) for i in range(3)]
    stats = classify_all(evs, FakeLLM("error"), BaselineClassifier(ALLOWED))
    assert stats["llm_errors"] == 3 and stats["fallback_used"] == 3
    assert all(e["categories"] == ["social"] and "classified_by_baseline" in e["flags"] for e in evs)
    assert all(e["youth"] == "unsure" for e in evs)  # "Quiz-kveld" alone says nothing about age


def test_budget_exhaustion_stops_llm_calls():
    evs = [good_event(id=f"tm:{i}", title="Quiz-kveld", source_categories=[]) for i in range(4)]
    llm = FakeLLM("budget")
    stats = classify_all(evs, llm, BaselineClassifier(ALLOWED))
    assert stats["budget_exhausted"] and llm.calls == 2  # no calls after the budget is hit
    assert evs[0]["categories"] == ["music"] and evs[3]["categories"] == ["social"]


# ---------------------------------------------------------------- Kulturnett normalizer (assumed format)

from harness.sources.kulturnett import normalize
from harness.sources.synthetic import generate


def test_normalize_maps_assumed_format():
    rec = {"id": "42", "tittel": " Konsert ", "beskrivelse": "Ring 912 34 567.", "start": "2026-11-05T19:00:00+01:00",
           "heldags": False, "sted": {"navn": "Hamar kulturhus", "kommune": "Hamar", "lat": "60.79", "lon": 11.06},
           "kategorier": ["Konsert", 7], "arrangor": "X", "pris": "Gratis",
           "url": "https://synthetic.example/hva-skjer/42", "status": "Publisert", "_expected": {"outcome": "accepted"}}
    ev = normalize(rec)
    assert ev["id"] == "kn:42" and ev["title"] == "Konsert" and ev["status"] == "active"
    assert ev["kommune"] == "Hamar" and ev["lat"] == 60.79 and ev["source_categories"] == ["Konsert"]
    assert "912 34 567" not in ev["description"] and "pii_removed" in ev["flags"]
    assert not any(k.startswith("_") for k in ev)  # test labels never reach the pipeline


def test_normalize_all_day_and_missing_place():
    ev = normalize({"id": "1", "tittel": "Utstilling", "start": "2026-11-07", "sted": None, "status": "avlyst"})
    assert ev["all_day"] and ev["start"] == "2026-11-07T00:00:00+01:00"
    assert ev["venue_name"] == "" and ev["kommune"] == "" and ev["status"] == "cancelled"


def test_normalize_naive_time_is_oslo():
    assert normalize({"id": "1", "start": "2026-07-01T12:00:00"})["start"] == "2026-07-01T12:00:00+02:00"


# ---------------------------------------------------------------- synthetic generator

def test_synthetic_is_deterministic_and_relative_to_now():
    later = datetime(2026, 12, 1, 8, 0, tzinfo=OSLO)
    a, b, c = generate(NOW), generate(NOW), generate(later)
    assert a == b
    assert a[0]["start"].startswith("2026-11-05") and c[0]["start"].startswith("2026-12-04")  # +3 days
    assert all("_expected" in r for r in a) and len({r["id"] for r in a}) == len(a)


# ---------------------------------------------------------------- label check and variance (eval/run_eval.py)

import json as _json

from eval.run_eval import check_labels, variance_summary


def _write_fixture(tmp_path, events):
    path = tmp_path / "f.json"
    path.write_text(_json.dumps({"events": events}), encoding="utf-8")
    return path


def test_label_check_accepts_valid_labels(tmp_path):
    path = _write_fixture(tmp_path, [
        {"id": "a", "_expected": {"outcome": "accepted", "categories": ["music"], "youth": "yes"}},
        {"id": "b", "_expected": {"outcome": "rejected", "reason": "in_past"}},
        {"id": "c", "_expected": {"outcome": "not_youth"}},
    ])
    assert check_labels(path)[1] == []


@pytest.mark.parametrize("label, fragment", [
    ({"outcome": "maybe"}, "is not one of"),
    ({"outcome": "accepted", "categories": ["sport"], "youth": "yes"}, "unknown categories"),
    ({"outcome": "accepted", "categories": ["music"]}, '"youth": "yes"'),
    ({"outcome": "rejected"}, "needs a \"reason\""),
    ({"outcome": "rejected", "reason": "missing_field:sted"}, "needs a \"reason\""),
    ({"outcome": "not_youth", "youth": "no"}, "must not have"),
])
def test_label_check_finds_problems(tmp_path, label, fragment):
    problems = check_labels(_write_fixture(tmp_path, [{"id": "x", "_expected": label}]))[1]
    assert problems and fragment in problems[0]


def test_label_check_ids_and_json(tmp_path):
    problems = check_labels(_write_fixture(tmp_path, [
        {"id": "", "_expected": {"outcome": "not_youth"}},
        {"id": "a", "_expected": {"outcome": "not_youth"}},
        {"id": "a", "_expected": {"outcome": "not_youth"}},
    ]))[1]
    assert any("non-empty" in p for p in problems) and any("unique" in p for p in problems)
    broken = tmp_path / "broken.json"
    broken.write_text('{"events": [ {"id": "a", } ]}', encoding="utf-8")
    assert "Not valid JSON" in check_labels(broken)[1][0]


def test_variance_summary_finds_flipping_events():
    def run(outcome_b, ok_b):
        return {"judgement_correct": f"{1 + ok_b}/2", "rows": [
            {"id": "a", "got": {"outcome": "accepted", "categories": ["music"]}, "outcome_correct": True},
            {"id": "b", "got": {"outcome": outcome_b, "categories": []}, "outcome_correct": ok_b},
        ]}
    v = variance_summary([run("accepted", True), run("needs_review", False), run("accepted", True)])
    assert v["judgement_correct_per_run"] == ["2/2", "1/2", "2/2"] and v["judgement_correct_mean"] == 1.67
    assert [u["id"] for u in v["unstable_events"]] == ["b"] and v["unstable_events"][0]["correct_in"] == "2/3"


# ---------------------------------------------------------------- self-consistency (stress-test repair for model variance)

from harness.classify import combine_answers


def test_combine_agreeing_answers_unchanged():
    a = {"categories": ["gaming", "social"], "youth": "yes"}
    assert combine_answers([a, {"categories": ["social", "gaming"], "youth": "yes"}]) == a


def test_combine_youth_disagreement_goes_to_review():
    r = combine_answers([{"categories": ["gaming"], "youth": "yes"}, {"categories": ["social"], "youth": "unsure"}])
    assert r["youth"] == "unsure" and r["disagreement"] == "youth" and r["categories"] == ["gaming", "social"]


def test_combine_category_disagreement_keeps_first_answer():
    r = combine_answers([{"categories": ["social", "arts_culture"], "youth": "yes"},
                         {"categories": ["social", "learning"], "youth": "yes"}])
    assert r == {"categories": ["social", "arts_culture"], "youth": "yes", "disagreement": "categories"}


def test_combine_category_disagreement_nothing_shared_does_not_cause_review():
    # Regression (9 Nov): "learning" vs "social" used to give no category -> review.
    r = combine_answers([{"categories": ["learning"], "youth": "yes"}, {"categories": ["social"], "youth": "yes"}])
    assert r["categories"] == ["learning"] and r["youth"] == "yes"


def test_youth_disagreement_routes_to_review_with_reason():
    ev = good_event(categories=["gaming"], youth="unsure", flags=["llm_disagreement:youth"])
    assert {"youth_unsure", "llm_disagreement"} <= set(validate_classification(ev, ALLOWED))


def test_classify_all_records_disagreement():
    class Wavering:
        name, calls, tokens = "llm", 0, 0

        def classify(self, ev):
            return {"categories": ["gaming"], "youth": "unsure", "disagreement": "youth"}

    evs = [good_event(id="tm:1")]
    stats = classify_all(evs, Wavering(), BaselineClassifier(ALLOWED))
    assert stats["llm_disagreements"] == 1 and "llm_disagreement:youth" in evs[0]["flags"]
    assert "disagreement" not in evs[0]
