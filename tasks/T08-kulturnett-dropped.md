# T08 · Kulturnett Innlandet API access (dropped)

**Status:** closed, not pursued. We asked for access but they answered us too late. 
On 12 Nov we dropped Kulturnett Innlandet as a source entirely because of legal
uncertainty about using their data. The project runs on synthetic data only,
in a format *inspired by* their "Hva skjer" calendar (agreed with the
lecturer). See the decision in `docs/white-paper-notes.md` and the README's
Sources table.

## What was planned
1. Email Kulturnett Innlandet: who we are, what the service does (youth events
   in the Hamar area, non-commercial, links back, no personal data), and ask
   for API/feed access, documentation and terms.
2. If granted: save a real response as a fixture, implement `fetch_live()` in
   `harness/sources/kulturnett.py`, and replace the assumed format in
   `harness/context/kulturnett_format.md` with the real one.
3. If refused: decide whether to continue on synthetic data only (allowed by
   the course brief) or add other sources (T09).

## Outcome
Step 3 applied: we continue on synthetic data only. Organizations can send
their events as a file instead (`fixtures/inbox/`, run with `--offline`).
`--source kulturnett` is kept only as a placeholder that stops with a message
(used by stress test 2, case 10 "source unreachable").

## Acceptance check
None left: the task is closed.
