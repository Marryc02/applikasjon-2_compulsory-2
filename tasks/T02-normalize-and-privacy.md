# T02 · Normalize events and remove contact details

**Status:** done
**Code:** `harness/normalize.py`, `harness/privacy.py` · **Spec:** `harness/context/event_schema.md`

## Goal
Convert each source record to the internal event format. Times in Europe/Oslo.
Descriptions max 300 characters. Remove emails and Norwegian phone numbers.

## Acceptance check
- `python -m pytest -k pii` passes: emails and phone numbers (`91234567`,
  `912 34 567.`, `+47 91 23 45 67`) are removed; times, dates, prices and postal codes are kept.
- `eval/test_pipeline.py`: no email or phone number from the fixture appears in `events.json`.

## Known gap
Personal **names** are not removed (fixture event SYN009 still contains "Kari").
