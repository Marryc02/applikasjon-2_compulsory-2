# T05 · Youth relevance and categories

**Status:** done (LLM path tested only with a fake client)
**Code:** `harness/classify.py` · **Context:** `harness/context/categories.md`, `harness/context/classify_prompt.md`

## Goal
For each valid event decide `youth` (`yes` / `no` / `unsure`: is it for people
about 13–25?) and 1–3 category IDs from `categories.md`. Claude does it when
`ANTHROPIC_API_KEY` is set; its reply is checked by code (JSON, known IDs,
max 3, valid `youth`), with one retry. On error or when the budget is spent,
the rule-based baseline decides instead and the event is flagged.

Routing: `youth = no` → `not_for_youth.json`; `unsure` or no category → `needs_review.json`.

## Acceptance check
- `python -m pytest -k "parse_llm or baseline or fall_back or budget"` passes.
- `python -m eval.run_eval` reports outcome accuracy and per-category precision/recall.
- Live LLM run: still to do (needs an Anthropic key).

## Warning
The baseline scores 100 % on the synthetic set, but the synthetic events and
the baseline's keywords were written by the same author (Claude). That number
says nothing about real data. See T10.
