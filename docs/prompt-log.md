# Prompt log

| Date | Who | Prompt | Outcome |
|------|-----|--------|---------|
| 2026-11-12 | jking + Claude | Plan a no-login web UI: read-only public page, organizer submission form, local-only admin page for review/approve (with per-event remove) | Plan written to `tasks/T11-web-ui.md` on branch `ui-inputs`; no code yet |
| 2026-11-12 | jking + Claude | Scope change: UI is only a read-only public page; organizers by email (manual entry), admin stays CLI; Kulturnett dropped | `tasks/T11-web-ui.md` rewritten; no code yet |
| 2026-11-12 | jking + Claude | Build the public page with Flask; Kulturnett cleanup postponed | `web/` + `tests/test_web.py` (15 tests), Flask added; 96 tests pass |
| 2026-11-12 | jking + Claude | Add a kommune filter that combines with the category filter | `web/` updated, 5 new tests; 101 tests pass |
