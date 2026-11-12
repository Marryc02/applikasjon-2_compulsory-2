# applikasjon-2_compulsory-2: Hamar Youth Events

An agentic workflow that collects events in the Hamar area, keeps the ones that
are for young people (about 13–25), checks and categorizes them, and publishes
them as a filterable calendar, subscribable iCal feeds per category (music,
sports, gaming, …) and a weekly digest in Norwegian. A person approves every
run before anything is published. The goal is to make low-threshold social
activities easier to find, as one small answer to youth loneliness.

**Status: walking skeleton on synthetic data.** The intended source is the
"Hva skjer" calendar from **Kulturnett Innlandet**. We have not received API
access yet, so the pipeline runs on a **simulated Kulturnett feed**: made-up
events in an assumed format (`harness/context/kulturnett_format.md`). When
access arrives, only `harness/sources/kulturnett.py` should need to change.

## Quick start

Requires Python 3.11+.

```bash
pip install -r requirements.txt
python -m harness run          # simulated feed, dates relative to today
python -m harness review       # decide on events the system wasn't sure about
python -m harness approve      # publish after review
python -m web                  # public page for approved events, http://127.0.0.1:5000
python -m pytest               # checks
python -m eval.run_eval        # evaluation against labelled synthetic events
```

Evaluation options:

```bash
python -m eval.run_eval --fixture fixtures/<test file>.json --check-only   # check labels only
python -m eval.run_eval --fixture fixtures/<test file>.json --classifier llm
python -m eval.run_eval --fixture fixtures/<test file>.json --classifier llm --repeat 5   # model variance
```

The labels in a fixture are always checked first; mistakes are reported per
event (exit code 2) instead of crashing the run.

Reproducible run on the saved fixture:

```bash
python -m harness run --offline fixtures/kulturnett_SYNTHETIC_2026-11-02.json --now 2026-11-02T08:00:00+01:00
```

Output:
- `out/staging/<run_id>/`: waiting for review: `events.json`, `digest.md`,
  `feeds/*.ics`, plus `not_for_youth.json`, `needs_review.json`,
  `rejected.json`, `duplicates.json` and `report.json` (counts, reasons, kill-switch status).
- `out/public/`: only after `approve`.
- `out/raw/<run_id>.json`: what was collected; can be replayed with `--offline`.
- `out/eval/`: evaluation results.

## Repository layout

| Folder | Job |
|---|---|
| `harness/` | The workflow: stages, prompts (`harness/context/`), sources (`harness/sources/`) |
| `tasks/` | One `.md` per task, each with an acceptance check |
| `eval/` | Checks (pytest) and the evaluation run (`run_eval.py`) |
| `fixtures/` | Saved inputs for offline, reproducible runs. `SYNTHETIC` = made up |
| `docs/meetings/` | Weekly meeting reports |
| `docs/prompt-log.md` | Agent output we corrected, challenged or rejected |
| `SPEC.md` | Problem, users, definition of success |

## Pipeline

| # | Stage | Code | LLM? | What it does |
|---|---|---|---|---|
| 1 | Collect | `sources/` | no | Simulated Kulturnett feed (or a saved file). Live Kulturnett: waiting for access |
| 2 | Normalize | `sources/kulturnett.py` | no | Converts to the internal format; removes emails and phone numbers; drops test labels |
| 3 | Validate | `validate.py` | no | Rejects missing fields, non-https links, cancelled, past, too far ahead, outside Hamar/Løten/Ringsaker/Stange |
| 4 | Dedupe | `dedupe.py` | no | Same normalized title + date + venue = duplicate |
| 5 | Classify | `classify.py` | yes | Is it for youth (yes/no/unsure)? Which 1–3 categories? Output checked by code; rule-based fallback |
| 6 | Stage | `publish.py` | no | Writes everything to `out/staging/`; kill switch can halt here |
| 7 | Publish | `publish.py` | no | Only on `python -m harness approve`. Before that, `python -m harness review` lets a person accept (with categories), mark as not for youth, or drop each event in the needs-review queue |

Classifier: `--classifier auto` (default) uses Claude when `ANTHROPIC_API_KEY`
is set in `.env`, otherwise the rule-based baseline.

Runs automatically every night via GitHub Actions (`.github/workflows/nightly.yml`)
on the simulated feed, staging only, followed by an evaluation run.

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
- **Kill switch:** if more than 50 % of collected events fail validation, or nothing is collected, the run halts and nothing is staged (exit code 2).

## Sources

| Source | Method | Terms | Status |
|---|---|---|---|
| Kulturnett Innlandet, Hva skjer | API (partner access) | TODO when access is granted | Requested access: TODO (see `tasks/T08`) |
| Simulated Kulturnett feed | `harness/sources/synthetic.py` | n/a (made up) | Used now |

## Related work

koigenhamar.no collects Hamar events nightly from open sources and cleans,
de-duplicates and categorizes them. It is not aimed at young people. This
project focuses on youth and on a tested, verifiable pipeline.

## Known limitations

- The Kulturnett format is assumed; the live source is not implemented yet.
- Personal **names** in event text are not removed (only emails and phone numbers).
- The baseline classifier uses simple keyword lists.
- The LLM classifier has only been tested with a fake client.
