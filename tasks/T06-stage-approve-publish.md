# T06 · Stage, human approval, publish

**Status:** done
**Code:** `harness/publish.py`, `harness/ics.py`

## Goal
Each run writes to `out/staging/<run_id>/`: `events.json`, `not_for_youth.json`,
`needs_review.json`, `rejected.json`, `duplicates.json`, `report.json`, a
Norwegian weekly digest and one iCal feed per category plus `all.ics`
(all-day events as `DTSTART;VALUE=DATE`). Nothing reaches `out/public/` until a
person runs `python -m harness approve` and confirms.

### Review queue
`python -m harness review` goes through `needs_review.json` one event at a
time: accept for youth (with 1–3 categories), not for youth, drop, or skip.
Decisions are confirmed before saving, logged in `report.json` under `review`,
and the feeds and digest are rebuilt. `approve` warns if events are still waiting.

## Acceptance check
- `python -m pytest -k "approval or ics or feeds or accounted or review"` passes.
