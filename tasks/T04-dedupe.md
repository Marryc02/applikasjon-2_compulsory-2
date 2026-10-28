# T04 · Remove duplicates

**Status:** done
**Code:** `harness/dedupe.py`

## Goal
Treat events with the same normalized title (case and punctuation ignored),
the same date and the same venue as one event. Keep the first; log the others
with `duplicate_of`.

## Acceptance check
- `python -m pytest -k dedupe` passes.
- On the fixture, SYN004 is removed as a duplicate of SYN001.
