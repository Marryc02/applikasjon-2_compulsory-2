# CLAUDE.md
Two-person course project (KIUA-2003) building an agentic workflow: collect,
validate, categorize and publish youth events in Hamar. See SPEC.md.

## Python Environment
This project uses a virtual environment located in `.venv\`. 
Do NOT try to activate the environment using scripts in the Scripts folder, as it will not persist across shell commands.

Instead, you MUST invoke the virtual environment's interpreter and tools directly using these specific paths:
- Run any script: `.venv\Scripts\python.exe <script.py>`
- Run package management: `.venv\Scripts\pip.exe install <package>`
- Run tests: `.venv\Scripts\pytest.exe`
- Run code quality tools: `.venv\Scripts\ruff.exe check`

Never use bare `python`, `pip`, or `pytest` commands. Always prefix with `.venv\Scripts\`.

## Layout
- `harness/`: the workflow. Stages: `sources/` (collect + `kulturnett.normalize`, with `privacy`)
  → `validate` → `dedupe` → `classify` → `publish`. `pipeline.py` wires them. Run with `python -m harness`.
- `harness/sources/`: `kulturnett.py` (live source: NOT available yet, format ASSUMED, see
  `harness/context/kulturnett_format.md`) and `synthetic.py` (simulated feed with `_expected` labels).
- `harness/context/`: files the workflow reads at run time. `categories.md` is the only
  place categories are defined. `classify_prompt.md` is the LLM prompt.
  `event_schema.md` defines the event format and validation rules.
- `tasks/`: one file per task with an acceptance check. Read the task file before working on a task.
- `eval/`: checks (pytest) and `run_eval.py` (evaluation against labelled fixtures).
- `fixtures/`: saved inputs for offline, reproducible runs. Files marked `SYNTHETIC` are made up.
- `out/`: run output (git-ignored). `out/staging/` = waiting for approval, `out/public/` = approved.

## Checks
- `python -m pytest`: must pass before every commit.
- `python -m harness run --offline fixtures/kulturnett_SYNTHETIC_2026-11-02.json --now 2026-11-02T08:00:00+01:00`: reproducible end-to-end run.
- `python -m eval.run_eval`: evaluation run.

## Rules
- Never edit anything in `eval/` without asking first.
- No personal data in code, fixtures, logs or prompts. No user accounts or subscriber lists.
- Sources: only official APIs, RSS/iCal feeds, or material organizers submit themselves. No web scraping.
- `_expected` labels are test data: they must never be read by any pipeline stage or appear in output.
- Never change an `_expected` label to make a test or evaluation pass.
- Nothing is published without human approval: only `python -m harness approve` writes to `out/public/`.
- Secrets live in `.env`, which is never committed or read by Claude. Copy it from
  `.env.example`. The program loads it at run time. Never print or log keys.
- Mechanically checkable things are checked in code, not by the LLM.
- Add a test for every bug fixed.
- Code and docs in English; user-facing output (digest, feed names) in Norwegian.
- Log notable prompts in `docs/prompt-log.md`.
