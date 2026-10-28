# T03 · Validate events (code only, no LLM)

**Status:** done
**Code:** `harness/validate.py` · **Rules:** `harness/context/event_schema.md`

## Goal
Reject events that are missing required fields, have a non-https link, are
cancelled/postponed, have no fixed date, are in the past, are more than 60 days
ahead, or are outside the Hamar area. Every rejection carries its reason(s).

## Acceptance check
- `python -m pytest -k "rejections or valid_event"` passes (one test per rule).
- On the fixture, exactly SYN005–SYN008, SYN010 and SYN012 are rejected, each with the expected reason.
