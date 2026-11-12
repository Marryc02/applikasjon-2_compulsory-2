# T12 · Unpublish a single event

**Status:** done (first version)
**Code:** `harness/publish.py` (`unpublish`, block list), `harness/pipeline.py`, `harness/__main__.py`
**Tests:** `tests/test_unpublish.py`

## Goal
A person who approved an event by mistake can take that one event down again,
from the command line (admin stays on the command line, see T11).

- `python -m harness unpublish` lists the published events with their IDs.
- `python -m harness unpublish <ID> [--reason TEXT] [--yes]` asks for
  confirmation, then removes the event from `out/public/events.json`, rebuilds
  the feeds and digest, and logs it under `unpublished` in `published.json`.
- The event is added to `out/blocked.json`. Since publishing is cumulative
  (each `approve` adds to `out/public/`), this is what stops it from coming back:
  - the pipeline rejects a blocked event with reason `unpublished_by_human`
    (after the kill-switch check, so it doesn't count as a source problem);
  - `approve` filters blocked events out, also from runs staged before the unpublish.
- Matched by ID or by title + date + venue (`dedupe_key`), so a copy sent in
  again under a new ID is caught too.
- The reason is free text: emails and phone numbers are stripped from it.

## Known limits
- Calendar apps remove the event only when they next refresh the feed.
- There is no `undo` command yet: to allow an event again, delete its entry
  from `out/blocked.json` and run + approve again.
- `out/blocked.json` is in the git-ignored `out/` folder, so it lives on the
  machine that runs the pipeline.

## Acceptance check
- `python -m pytest -k unpublish` passes.
