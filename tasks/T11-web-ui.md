# T11 · Public web page for approved events

**Status:** done (first version)
**Code:** `web/` (Flask) · **Tests:** `tests/test_web.py`

## Decisions (2026-11-12)
- The only UI is a **read-only public page** for young people.
- **No organizer form.** Organizations send events by email or similar, and we
  add them by hand. A submission page may come later if the project continues.
- **Admin stays on the command line** (`python -m harness review` / `approve`).
- Approval flow is unchanged: the model's `yes` events wait for run approval;
  `unsure` events go through `review` first. Nothing is public until `approve`.
- Kulturnett is dropped as a source (see "Out of scope").

## Goal
A Norwegian web page that shows the events in the latest approved run.

- Reads only `out/public/` (`published.json`, `events.json`, `feeds/`).
  Never reads `out/staging/`. Shows an empty state before anything is approved.
- Lists upcoming events by day: time, title (linking to `source_url`), venue,
  kommune, price, categories.
- Filter by category (IDs from `harness/context/categories.md`, Norwegian labels)
  and by kommune (`area.kommuner` in `config.toml`). The two filters combine.
- One subscribe link per category `.ics` feed, plus `all.ics`.
- Works on a phone. No accounts, no cookies, no tracking, no personal data.

## Acceptance check
- `python -m pytest -k web` passes, with tests in `tests/` (added to `testpaths`
  in `pytest.ini`; `eval/` is not touched) for:
  - only events from `out/public/events.json` are shown; nothing from staging;
  - the category filter and feed links match `categories.md`;
  - the kommune filter matches `config.toml`, and both filters combine;
  - the empty state when nothing is published;
  - no emails or phone numbers in the page.
- Manual: run the pipeline, `approve`, open the page, see the events and
  subscribe to a feed in a calendar app.

## Out of scope (separate tasks)
- Removing Kulturnett from the code and docs, and deciding the new event sources.
- A way to add events from organizers by hand.
- Organizer submission page, admin web page.
