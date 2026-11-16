# T11 · Public web page for approved events

**Status:** done
**Code:** `web/` (Flask) · **Tests:** `tests/test_web.py`

## Decisions (2026-11-12)
- The only UI is a **read-only public page** for young people.
- **No organizer form.** Organizations send events by email or similar, and we
  add them by hand. A submission page may come later if the project continues.
- **Admin stays on the command line** (`python -m harness review` / `approve` / `unpublish`).
- Approval flow is unchanged: the model's `yes` events wait for run approval;
  `unsure` events go through `review` first. Nothing is public until `approve`.
- Kulturnett is dropped as a source (see "Out of scope").

## Goal
A Norwegian web page that shows all approved events that haven't happened yet
(from every approved run; changed 12 Nov, before that only the latest run).

- Reads only `out/public/` (`published.json`, `events.json`, `feeds/`).
  Never reads `out/staging/`. Shows an empty state before anything is approved.
- Lists upcoming events by day: time, title (linking to `source_url`), venue,
  kommune, price, categories.
- Filter by category (IDs from `harness/context/categories.md`, Norwegian labels)
  and by kommune (`area.kommuner` in `config.toml`). The two filters combine.
- One subscribe link per category `.ics` feed, plus `all.ics`.
- "Legg i kalender (.ics)" per event: downloads only that event
  (`/arrangement/<id>.ics`). Only upcoming events in `out/public/`; anything
  else is 404. Description scrubbed for contact details (added 16 Nov).
- "Vis på kart" per event with valid `lat`/`lon`: an OpenStreetMap embed
  (no API key) opens under the event, loaded only on click (`web/static/map.js`).
  Opening one map closes the other. Without JavaScript the button is hidden.
  CSP allows only our own script and frames from www.openstreetmap.org (added 16 Nov).
- Works on a phone. No accounts, no cookies, no tracking, no personal data.

## Acceptance check
- `python -m pytest -k web` passes, with tests in `tests/` (added to `testpaths`
  in `pytest.ini`; `eval/` is not touched) for:
  - only events from `out/public/events.json` are shown; nothing from staging;
  - the category filter and feed links match `categories.md`;
  - the kommune filter matches `config.toml`, and both filters combine;
  - the empty state when nothing is published;
  - no emails or phone numbers in the page;
  - each event's `.ics` download holds exactly that event, only after approval,
    never for past or unknown events, and without contact details;
  - the map button appears only for events with valid coordinates, nothing is
    loaded from OpenStreetMap on page load, and the CSP is as narrow as above.
- Manual: open two maps in a row; the first one closes.
- Manual: run the pipeline, `approve`, open the page, see the events and
  subscribe to a feed in a calendar app.

## Out of scope (separate tasks)
- ~~Removing Kulturnett from the docs~~ (done 12 Nov: README, SPEC, config, T01,
  T08). File and option names that say `kulturnett` remain and refer to the format.
- ~~A way to add events from organizers by hand~~ (done: put the file in
  `fixtures/inbox/` and run it with `--offline`).
- New event sources (T09), organizer submission page, admin web page: not planned.
