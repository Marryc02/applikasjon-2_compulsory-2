# T01 · Collect events (synthetic data)

**Status:** done.
**Code:** `harness/sources/` · **Format:** `harness/context/kulturnett_format.md`
(inspired by Kulturnett Innlandet's "Hva skjer" calendar; not their data)

## Goal
Collect upcoming events in the Hamar area. Kulturnett Innlandet was dropped as
a source (see T08), so the events come from:
- `harness/sources/synthetic.py`: 22 made-up events per run, with dates
  relative to the run time and an `_expected` label on each (the outcome a
  correct pipeline should produce).
- A saved file with `--offline <file>`: the test sets in `fixtures/testing/`,
  or a file from an organization in `fixtures/inbox/`. A file can carry its
  own run time (`"_run_time"`), so its fixed dates aren't rejected as past.

Every run saves what it collected to `out/raw/<run_id>.json`, so it can be
replayed with `--offline`. Data that can't be read (not JSON, no `events`
list) stops the run with a plain message, and records that aren't events are
rejected one by one as `invalid_record` (stress test 2, repairs R1 and R2).

## Acceptance check
- `python -m harness run` prints `[1 collect]   22 events from synthetic (made-up events)`.
- `python -m harness run --offline fixtures/testing/kulturnett_HUMAN_markus.json`
  prints `Run time from the file: 2026-11-02T08:00:00+01:00` and stages the run.
- `python -m harness run --source kulturnett` exits with code 3 and a message
  (placeholder, no crash).
- `python -m eval.stress_source` reports 0 crashes.
- `python -m pytest -k "synthetic or fixture_matches"` passes.
