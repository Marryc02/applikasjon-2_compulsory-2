# T03 · Validate events (code only, no LLM)

**Status:** done
**Code:** `harness/validate.py` · **Rules:** `harness/context/event_schema.md`

## Goal
Reject events that are missing required fields, have a non-https link, are not
active (cancelled/postponed), are in the past, are more than 60 days ahead, or
are outside the Hamar area (Hamar, Løten, Ringsaker, Stange). Every rejection carries its reason(s).

## Acceptance check
- `python -m pytest -k "rejections or municipalities or all_day_event"` passes.
- `eval/test_pipeline.py::test_rejections_and_duplicates_match_labels` passes:
  exactly the 7 events labelled `rejected` are rejected, each with the labelled reason.
