# T06 · Stage, human approval, publish

**Status:** done
**Code:** `harness/publish.py`, `harness/ics.py`

## Goal
Each run writes to `out/staging/<run_id>/`: events, rejected, duplicates,
needs_review, report, a Norwegian weekly digest and one iCal feed per category
plus `all.ics`. Nothing reaches `out/public/` until a person runs
`python -m harness approve` and confirms.

## Acceptance check
- `python -m pytest -k "approval or ics"` passes: nothing in `out/public/` before
  approval; a run cannot be approved twice; feeds are valid iCal (escaping, 75-octet lines, UTC times).
- On the fixture, `gaming.ics` contains exactly 1 event and `all.ics` 5.
