# T08 · First live run (humans)

**Status:** TODO
**Needs:** a Ticketmaster API key in `.env` (Claude may not read `.env`).

## Steps
1. Get a key at https://developer.ticketmaster.com/ and read the Terms of Use.
   Fill in the Ticketmaster row of the source table in `README.md`.
2. `python -m harness run --classifier baseline`
3. Look at `out/staging/<run_id>/`: how many Hamar events? Are rejections right?
4. Copy `out/raw/<run_id>.json` to `fixtures/ticketmaster_<date>_REAL.json`
   so the real input can be replayed offline.
5. With an Anthropic key: run again with `--classifier llm` and compare categories.
6. Write down surprises in this week's meeting report.

## Acceptance check
- A live run finishes with exit code 0 (or halts with a reason you understand).
- A real response is saved in `fixtures/` and `python -m harness run --offline fixtures/<file>` reproduces the run.
