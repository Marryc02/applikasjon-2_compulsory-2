"""Checks for the public web page (T11): shows only approved events, never writes."""
import html
import json
from datetime import datetime
from pathlib import Path

import pytest

from harness.classify import load_categories
from harness.config import OSLO, load_config
from harness.pipeline import run
from harness.publish import approve, write_outputs
from web.app import create_app

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "testing" / "kulturnett_SYNTHETIC_2026-11-02.json"
NOW = datetime(2026, 11, 2, 8, 0, tzinfo=OSLO)
ALLOWED = sorted(load_categories()[0])


def _event(i, title, start, cats, **extra):
    return {"id": f"test:{i}", "source": "test", "source_url": f"https://example.org/{i}",
            "title": title, "start": start, "all_day": False, "status": "active",
            "venue_name": "Kulturhuset", "kommune": "Hamar", "categories": cats,
            "youth": "yes", "flags": [], **extra}


def _publish(base: Path, events: list[dict]) -> Path:
    """Write a public folder the way approve() leaves it."""
    public = base / "public"
    write_outputs(public, events, ALLOWED, NOW)
    (public / "published.json").write_text(
        json.dumps({"run_id": "test", "approved_at": "2026-11-02T09:00:00+01:00"}), encoding="utf-8")
    return public


def _client(public: Path, now=NOW):
    return create_app(public_dir=public, now_fn=lambda: now).test_client()


def _page(client, path="/") -> str:
    resp = client.get(path)
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def _pipeline(tmp_path):
    report = run(load_config(), NOW, offline_file=FIXTURE, classifier="baseline",
                 base=tmp_path, log=lambda *_: None)
    return tmp_path / "staging" / report["run_id"]


def _titles(path: Path) -> set[str]:
    return {e["title"] for e in json.loads(path.read_text(encoding="utf-8"))}


def test_empty_state_when_nothing_is_published(tmp_path):
    page = _page(_client(tmp_path / "public"))
    assert "Ingen arrangementer er publisert ennå" in page


def test_staged_run_is_not_shown_before_approval(tmp_path):
    run_dir = _pipeline(tmp_path)
    page = _page(_client(tmp_path / "public"))
    assert "Ingen arrangementer er publisert ennå" in page
    for title in _titles(run_dir / "events.json"):
        assert html.escape(title) not in page


def test_approved_run_shows_exactly_the_accepted_events(tmp_path):
    run_dir = _pipeline(tmp_path)
    accepted = _titles(run_dir / "events.json")
    hidden = set()
    for name in ("rejected.json", "not_for_youth.json", "needs_review.json"):
        hidden |= _titles(run_dir / name)
    approve(run_dir, base=tmp_path)

    page = _page(_client(tmp_path / "public"))
    assert accepted
    for title in accepted:
        assert html.escape(title) in page
    for title in hidden - accepted:
        assert html.escape(title) not in page


def test_category_filter(tmp_path):
    public = _publish(tmp_path, [
        _event(1, "Konsert på huset", "2026-11-03T19:00:00+01:00", ["music"]),
        _event(2, "Brettspillkveld", "2026-11-04T18:00:00+01:00", ["gaming", "social"]),
    ])
    client = _client(public)
    music = _page(client, "/?kategori=music")
    assert "Konsert på huset" in music and "Brettspillkveld" not in music
    # Unknown category: ignored, everything shown.
    everything = _page(client, "/?kategori=finnesikke")
    assert "Konsert på huset" in everything and "Brettspillkveld" in everything


def _mixed(tmp_path):
    return _publish(tmp_path, [
        _event(1, "Pizzakveld Stange", "2026-11-03T18:00:00+01:00", ["food", "social"], kommune="Stange"),
        _event(2, "Matkurs Hamar", "2026-11-04T18:00:00+01:00", ["food", "learning"], kommune="Hamar"),
        _event(3, "Konsert Stange", "2026-11-05T19:00:00+01:00", ["music"], kommune="Stange"),
        _event(4, "Skitur Løten", "2026-11-06T10:00:00+01:00", ["outdoors"], kommune="Løten"),
    ])


def _shown(page: str) -> set[str]:
    names = {"Pizzakveld Stange", "Matkurs Hamar", "Konsert Stange", "Skitur Løten"}
    return {n for n in names if n in page}


def test_kommune_filter(tmp_path):
    page = _page(_client(_mixed(tmp_path)), "/?kommune=Stange")
    assert _shown(page) == {"Pizzakveld Stange", "Konsert Stange"}


def test_category_and_kommune_filters_combine(tmp_path):
    client = _client(_mixed(tmp_path))
    assert _shown(_page(client, "/?kategori=food&kommune=Stange")) == {"Pizzakveld Stange"}
    assert _shown(_page(client, "/?kategori=food")) == {"Pizzakveld Stange", "Matkurs Hamar"}
    nothing = _page(client, "/?kategori=outdoors&kommune=Hamar")
    assert _shown(nothing) == set()
    assert "Ingen kommende arrangementer i kategorien Friluftsliv i Hamar" in nothing


def test_unknown_kommune_is_ignored(tmp_path):
    page = _page(_client(_mixed(tmp_path)), "/?kommune=Oslo")
    assert len(_shown(page)) == 4


def test_filter_links_keep_the_other_filter(tmp_path):
    page = _page(_client(_mixed(tmp_path)), "/?kategori=food&kommune=Stange")
    # Switching place keeps the category, switching category keeps the place.
    assert "/?kategori=food&amp;kommune=L%C3%B8ten" in page
    assert "/?kategori=music&amp;kommune=Stange" in page
    # "Alle" / "Alle steder" clear only their own filter.
    assert 'href="/?kommune=Stange"' in page
    assert 'href="/?kategori=food"' in page


def test_kommune_filters_come_from_config(tmp_path):
    page = _page(_client(_publish(tmp_path, [])))
    for kommune in load_config()["area"]["kommuner"]:
        assert f">{kommune}</a>" in page


def test_every_category_from_categories_md_has_a_filter_and_a_feed(tmp_path):
    page = _page(_client(_publish(tmp_path, [])))
    for cat in ALLOWED:
        assert f"kategori={cat}" in page
        assert f"/feeds/{cat}.ics" in page
    assert "/feeds/all.ics" in page


def test_past_events_are_hidden(tmp_path):
    public = _publish(tmp_path, [
        _event(1, "Var i går", "2026-11-01T19:00:00+01:00", ["music"]),
        _event(2, "Er i morgen", "2026-11-03T19:00:00+01:00", ["music"]),
    ])
    page = _page(_client(public))
    assert "Er i morgen" in page and "Var i går" not in page


def test_no_contact_details_in_page(tmp_path):
    public = _publish(tmp_path, [_event(1, "Kurs", "2026-11-03T19:00:00+01:00", ["learning"],
                                        description="Spørsmål? Send til ola@example.no eller ring 912 34 567.")])
    page = _page(_client(public))
    assert "ola@example.no" not in page and "912 34 567" not in page


def test_non_https_link_is_not_rendered(tmp_path):
    public = _publish(tmp_path, [_event(1, "Tur", "2026-11-03T10:00:00+01:00", ["outdoors"],
                                        source_url="javascript:alert(1)")])
    page = _page(_client(public))
    assert "Tur" in page and "javascript:" not in page


def test_html_in_event_text_is_escaped(tmp_path):
    public = _publish(tmp_path, [_event(1, "<script>x()</script>", "2026-11-03T10:00:00+01:00", ["social"])])
    page = _page(_client(public))
    assert "<script>x()" not in page and "&lt;script&gt;" in page


def test_feeds_are_served_as_calendars(tmp_path):
    public = _publish(tmp_path, [_event(1, "Konsert", "2026-11-03T19:00:00+01:00", ["music"])])
    client = _client(public)
    for name in ["all", *ALLOWED]:
        resp = client.get(f"/feeds/{name}.ics")
        assert resp.status_code == 200
        assert resp.mimetype == "text/calendar"
        assert resp.get_data(as_text=True).startswith("BEGIN:VCALENDAR")


@pytest.mark.parametrize("path", ["/feeds/finnesikke.ics", "/feeds/..%2Fevents.ics", "/feeds/../events.json"])
def test_unknown_feeds_are_not_served(tmp_path, path):
    client = _client(_publish(tmp_path, []))
    assert client.get(path).status_code == 404


def test_no_feeds_before_approval(tmp_path):
    _pipeline(tmp_path)
    assert _client(tmp_path / "public").get("/feeds/all.ics").status_code == 404


def test_page_never_writes(tmp_path):
    public = _publish(tmp_path, [_event(1, "Konsert", "2026-11-03T19:00:00+01:00", ["music"])])
    before = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*")}
    client = _client(public)
    for path in ["/", "/?kategori=music", "/feeds/all.ics", "/feeds/music.ics", "/feeds/nope.ics"]:
        client.get(path)
    after = {p: p.stat().st_mtime_ns for p in tmp_path.rglob("*")}
    assert before == after
