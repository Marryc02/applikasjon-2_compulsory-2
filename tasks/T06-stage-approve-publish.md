# T06 · Stage, human approval, publish

**Status:** done
**Code:** `harness/publish.py`, `harness/ics.py`

## Goal
Each run writes to `out/staging/<run_id>/`: `events.json`, `not_for_youth.json`,
`needs_review.json`, `rejected.json`, `duplicates.json`, `report.json`, a
Norwegian weekly digest and one iCal feed per category plus `all.ics`
(all-day events as `DTSTART;VALUE=DATE`). Nothing reaches `out/public/` until a
person runs `python -m harness approve` and confirms.

### Publishing is cumulative (12 Nov)
`approve` adds the run's events to what is already in `out/public/` instead of
replacing it: the same event (same ID, or same title + date + venue) from a
newer run replaces the older version, events that started before today are
dropped, and `published.json` lists every approved run. A published event can
be taken down again with `unpublish` (T12).

The run ID is the real start time, also when `--now` pretends another time, so
`review` and `approve` always pick the newest run.

### Review queue
`python -m harness review` goes through `needs_review.json` one event at a
time: accept for youth (with 1–3 categories), not for youth, drop, or skip.
Decisions are confirmed before saving, logged in `report.json` under `review`,
and the feeds and digest are rebuilt. `approve` warns if events are still waiting.

## Acceptance check
- `python -m pytest -k "approval or ics or feeds or accounted or review"` passes.
