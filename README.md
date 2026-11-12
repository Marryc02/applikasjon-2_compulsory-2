# applikasjon-2_compulsory-2: Hamar Youth Events

An agentic workflow that collects events in the Hamar area, keeps the ones that
are for young people (about 13–25), checks and categorizes them, and publishes
them as a filterable calendar, subscribable iCal feeds per category (music,
sports, gaming, …) and a weekly digest in Norwegian. A person approves every
run before anything is published. The goal is to make low-threshold social
activities easier to find, as one small answer to youth loneliness.

**Status: runs on synthetic data only.** All events are made up. Their format
is *inspired by* the public "Hva skjer" calendar from Kulturnett Innlandet
(described in `harness/context/kulturnett_format.md`), but this project does
**not** use Kulturnett Innlandet as a data source and contains none of their
data. We dropped Kulturnett as a source because of legal uncertainty about
using their data. The file and option names that still say `kulturnett` refer
to this format, not to their service. A real source (API, RSS or iCal) would
be added as a new module in `harness/sources/`.

## Quick start

Requires Python 3.11+.

```bash
pip install -r requirements.txt
python -m harness run          # synthetic events, dates relative to today
python -m harness review       # decide on events the system wasn't sure about
python -m harness approve      # publish after review
python -m harness unpublish    # list published events; add an ID to take one down
python -m web                  # public page with the approved events: http://127.0.0.1:5000
python -m pytest               # checks
python -m eval.run_eval        # evaluation against labelled synthetic events
python -m eval.make_stress_inputs   # stress test 2: write broken source data
python -m eval.stress_source        # stress test 2: run the pipeline on it
```

Evaluation options:

```bash
python -m eval.run_eval --fixture fixtures/testing/<test file>.json --check-only   # check labels only
python -m eval.run_eval --fixture fixtures/testing/<test file>.json --classifier llm
python -m eval.run_eval --fixture fixtures/testing/<test file>.json --classifier llm --repeat 5   # model variance
```

The labels in a fixture are always checked first; mistakes are reported per
event (exit code 2) instead of crashing the run.

Reproducible run on the saved fixture:

```bash
python -m harness run --offline fixtures/testing/kulturnett_SYNTHETIC_2026-11-02.json
```

A saved file can carry the run time it was made for (`"_run_time"`); `--offline`
then uses it, so its fixed dates aren't rejected as past. `--now` overrides it.
Files the pipeline saves in `out/raw/` include it automatically.

Output:
- `out/staging/<run_id>/`: waiting for review: `events.json`, `digest.md`,
  `feeds/*.ics`, plus `not_for_youth.json`, `needs_review.json`,
  `rejected.json`, `duplicates.json` and `report.json` (counts, reasons, kill-switch status).
- `out/public/`: every approved event that hasn't happened yet, from all approved
  runs. Each `approve` adds a run's events (a newer version of the same event
  replaces the older one) and drops past events. The web page and feeds are built from it.
  `unpublish <ID>` removes one event again and logs it in `published.json`.
- `out/blocked.json`: events a person has unpublished. Later runs reject them
  (`unpublished_by_human`) and `approve` filters them out, matched by ID or by
  title + date + venue.
- `out/raw/<run_id>.json`: what was collected; can be replayed with `--offline`.
- `out/eval/`: evaluation results.

## Repository layout

| Folder | Job |
|---|---|
| `harness/` | The workflow: stages, prompts (`harness/context/`), sources (`harness/sources/`) |
| `tasks/` | One `.md` per task, each with an acceptance check |
| `web/` | Public web page (Flask) that shows the approved events |
| `eval/` | Checks (pytest), the evaluation run (`run_eval.py`) and stress test 2 (`make_stress_inputs.py`, `stress_source.py`) |
| `tests/` | Checks for the web page (`test_web.py`) |
| `fixtures/testing/` | Saved inputs for offline, reproducible runs and tests. `SYNTHETIC` = made up, `HUMAN` = written by us, `stress/` = broken data for stress test 2 |
| `fixtures/inbox/` | Event files received from organizations. Git-ignored (may contain personal data); run with `python -m harness run --offline fixtures/inbox/<file>.json` |
| `docs/meetings/` | Meeting reports (one per meeting) |
| `docs/results/` | Saved evaluation and stress-test results (see its README) |
| `docs/prompt-log.md` | Prompts to coding agents (claude.ai and Claude Code) and what came out, incl. output we corrected, challenged or rejected |
| `SPEC.md` | Problem, users, definition of success |

## Pipeline

| # | Stage | Code | LLM? | What it does |
|---|---|---|---|---|
| 1 | Collect | `sources/` | no | Synthetic events (or a saved file). Stops with a plain message if the data can't be read |
| 2 | Normalize | `sources/kulturnett.py` | no | Converts to the internal format; removes emails and phone numbers; drops test labels |
| 3 | Validate | `validate.py` | no | Rejects missing fields, non-https links, cancelled, past, too far ahead, outside Hamar/Løten/Ringsaker/Stange |
| 4 | Dedupe | `dedupe.py` | no | Same normalized title + date + venue = duplicate |
| 5 | Classify | `classify.py` | yes | Is it for youth (yes/no/unsure)? Which 1–3 categories? Output checked by code; rule-based fallback |
| 6 | Stage | `publish.py` | no | Writes everything to `out/staging/`; kill switch can halt here |
| 7 | Publish | `publish.py` | no | Only on `python -m harness approve`. Before that, `python -m harness review` lets a person accept (with categories), mark as not for youth, or drop each event in the needs-review queue. Afterwards, `python -m harness unpublish <ID>` takes one event down and blocks it from coming back |
| 8 | Show | `web/` | no | The public web page shows all approved upcoming events, read from `out/public/` |

Classifier: `--classifier auto` (default) uses Claude when `ANTHROPIC_API_KEY`
is set in `.env`, otherwise the rule-based baseline.

Runs automatically every night via GitHub Actions (`.github/workflows/nightly.yml`)
on synthetic events, staging only, followed by an evaluation run.

## Public web page

```bash
python -m web                  # http://127.0.0.1:5000 (--host / --port to change)
```

A read-only page in Norwegian for young people, showing **only approved
events**: it reads `out/public/` (written only by `approve`) and never
`out/staging/`. It shows every approved event that hasn't happened yet, from
all approved runs. Before anything is approved it shows an empty page.

- Upcoming events grouped by day: time, title (links to the event's source
  page), venue, kommune, price and categories.
- Filter by category and by kommune; the two filters can be combined.
- One subscribe link per category feed, plus one with all events
  (`/feeds/<category>.ics`, `/feeds/all.ics`).
- No accounts, no cookies, no tracking. Descriptions are run through the
  privacy filter once more before they are shown.
- Admin (review and approve) stays on the command line.
- Uses Flask's development server and listens only on your own computer by
  default; real hosting would need a proper web server.

Organizations can send their events as a file (e.g. by email). A person puts
it in `fixtures/inbox/` and runs it through the pipeline with `--offline`;
it then goes through review and approval like any other run.

## Synthetic data

`harness/sources/synthetic.py` makes 22 events per run: 10 youth events, 3 for
other audiences, 1 unclear, 1 duplicate and 7 that must be rejected (one also
contains contact details, one a prompt-injection attempt). Each carries an
`_expected` label used by `eval/run_eval.py` and dropped before the pipeline sees it.
**The events, labels and baseline keywords were all written by Claude**, so the
baseline's score on them is not a real measurement (see `tasks/T10`).

## Safety (first version)

- **Permissions:** the pipeline reads only its source and `harness/context/`, and writes only under `out/`.
- **Secrets:** environment variables only (`.env`, git-ignored); never logged.
- **Cost:** per run, at most `max_llm_calls` LLM calls and `max_total_tokens` tokens (`config.toml`); then the baseline takes over.
- **Prompt injection:** event text is passed as data; the reply must match a strict format or it is rejected and the baseline decides.
- **Human-in-the-loop:** nothing reaches `out/public/` without `approve`; uncertain events wait in a review queue that a person works through with `review` (every decision is logged in the run's `report.json`).
- **Kill switch:** if more than 50 % of collected events fail validation, or nothing is collected, the run halts and nothing is staged (exit code 2). The message names the most common reason, e.g. a missing field or the wrong region.

## Sources

| Source | Method | Terms | Status |
|---|---|---|---|
| Synthetic events (format inspired by Kulturnett Innlandet's "Hva skjer") | `harness/sources/synthetic.py` | n/a (made up, no real data) | Used |
| Kulturnett Innlandet | – | – | **Not used.** Dropped because of legal uncertainty; only the format inspired our synthetic data |

## Related work

koigenhamar.no collects Hamar events nightly from open sources and cleans,
de-duplicates and categorizes them. It is not aimed at young people. This
project focuses on youth and on a tested, verifiable pipeline.

## Known limitations

- There is no live source: the system has only been run on synthetic data.
- Personal **names** in event text are not removed (only emails and phone numbers).
- The baseline classifier uses simple keyword lists.
- The LLM classifier (Claude Haiku) has been evaluated on 13 judgement events in two test sets; the sample is small.
