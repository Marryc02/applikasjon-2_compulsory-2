# applikasjon-2_compulsory-2: Hamar Youth Events

An agentic workflow that collects youth events in Hamar from official
machine-readable sources, validates and categorizes them, and publishes them
as a filterable calendar, subscribable iCal feeds per category (music, sports,
gaming, …) and a weekly digest. A person approves every run before anything is
published. The goal is to make it easier for young people in Hamar to find
low-threshold social activities, as one small answer to youth loneliness.

**Status: walking skeleton.** One path runs end to end:
Ticketmaster API → normalize → validate → dedupe → classify → staging → human approval → published feeds.

## Quick start (no API keys needed)

Requires Python 3.11+.

```bash
pip install -r requirements.txt
python -m harness run --offline --now 2026-11-02T08:00:00+01:00
python -m harness approve
python -m pytest
```

`--offline` uses `fixtures/ticketmaster_sample_SYNTHETIC.json`, a set of **synthetic**
events in the Ticketmaster API format. Replay any saved input with `--offline <file>`. `--now` fixes the run time so the result
is the same every time.

Output:
- `out/staging/<run_id>/`: what the run produced, waiting for review:
  `events.json`, `digest.md`, `feeds/*.ics`, plus `rejected.json`,
  `duplicates.json`, `needs_review.json` and `report.json` (counts, reasons, kill-switch status).
- `out/public/`: only after `approve`: the published events, digest and feeds.

## Repository layout

| Folder | Job |
|---|---|
| `harness/` | The workflow: stages, prompts (`harness/context/`), tools |
| `tasks/` | One `.md` per task, each with an acceptance check |
| `eval/` | Checks (pytest); later the test set and evaluation harness |
| `fixtures/` | Saved inputs for offline, reproducible runs |
| `docs/meetings/` | Weekly meeting reports |
| `docs/prompt-log.md` | Agent output we corrected, challenged or rejected |
| `SPEC.md` | Problem, users, definition of success |

## Live run

1. Get a free API key at <https://developer.ticketmaster.com/> (and, for the
   LLM classifier, an Anthropic API key).
2. `cp .env.example .env` and fill in the keys. `.env` is git-ignored.
3. `python -m harness run`
4. To make the run reproducible, copy `out/raw/<run_id>.json` into `fixtures/` and
   replay it with `python -m harness run --offline fixtures/<file> --now <run time>`.

Classifier choice: `--classifier auto` (default) uses the LLM when
`ANTHROPIC_API_KEY` is set, otherwise the rule-based baseline. Force one with
`--classifier llm` or `--classifier baseline`.

## Pipeline

| # | Stage | Module | LLM? | What it does |
|---|---|---|---|---|
| 1 | Collect | `fetch_ticketmaster.py` | no | Events within 25 km of Hamar, next 60 days. Retries on 429/5xx. Saves raw data to `out/raw/` |
| 2 | Normalize | `normalize.py` | no | Converts to the internal format (`harness/context/event_schema.md`); removes emails and phone numbers |
| 3 | Validate | `validate.py` | no | Rejects missing fields, cancelled, past, too far ahead, outside the area, no fixed date |
| 4 | Dedupe | `dedupe.py` | no | Same normalized title + date + venue = duplicate |
| 5 | Classify | `classify.py` | yes | Claude assigns 1–3 categories from `harness/context/categories.md`; output is checked by code; falls back to rule-based baseline |
| 6 | Stage | `publish.py` | no | Writes everything to `out/staging/`; kill switch can halt here |
| 7 | Publish | `publish.py` | no | Only on `python -m harness approve` |

Runs automatically every night via GitHub Actions (`.github/workflows/nightly.yml`),
staging only. Add `TICKETMASTER_API_KEY` and `ANTHROPIC_API_KEY` as repository secrets.

## Safety (first version)

- **Permissions:** the pipeline only reads the Ticketmaster API and `context/`, and only writes under `out/`.
- **Secrets:** environment variables only; the API key is never included in logs or error messages.
- **Cost:** per run, at most `max_llm_calls` LLM calls and `max_total_tokens` tokens (`config.toml`); after that the baseline classifier takes over.
- **Human-in-the-loop:** nothing reaches `out/public/` without `approve`.
- **Kill switch:** if more than 70 % of fetched events fail validation (or nothing is fetched), the run halts and nothing is staged. Exit code 2.

## Sources

| Source | Method | Terms checked | Decision |
|---|---|---|---|
| Ticketmaster Discovery API | Official API, free key | TODO: read Terms of Use when getting the key | Used |
| _Hamar RSS/iCal feeds_ | _to be found_ | | |
| _Organizer submissions_ | _planned_ | | |

## Known limitations

- Personal **names** in event text are not removed (only emails and phone numbers).
- The baseline classifier uses simple keywords and can misfire (e.g. "band" in "bandy").
- Ticketmaster mostly lists larger ticketed events, not free drop-in youth activities.
- The fixture's quiz event contains a prompt-injection string. It is kept on
  purpose as a stress-test case for the LLM classifier.
