# T02 · Normalize records and remove contact details

**Status:** done (for our format, inspired by Kulturnett Innlandet's calendar)
**Code:** `harness/sources/kulturnett.py` (`normalize`), `harness/privacy.py` · **Spec:** `harness/context/event_schema.md`

## Goal
Convert each source record to the internal event format. Times in
Europe/Oslo; all-day events start at midnight. Descriptions max 300 characters.
Remove emails and Norwegian phone numbers. Drop test labels (`_expected`).
A record that isn't an event at all (text, a number, `null`) is rejected on its
own as `invalid_record` instead of crashing the run (stress test 2, repair R2).

## Acceptance check
- `python -m pytest -k "pii or normalize"` passes.
- `eval/test_pipeline.py::test_no_personal_data_or_labels_in_output` passes.

## Known gap
Personal **names** are not removed (synthetic event "Tegneverksted" still contains "Kari").
