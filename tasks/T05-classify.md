# T05 · Youth relevance and categories

**Status:** done. Tested live with Claude Haiku (`claude-haiku-5-5`) on 9 and 12 Nov.
**Code:** `harness/classify.py` · **Context:** `harness/context/categories.md`, `harness/context/classify_prompt.md`

## Goal
For each valid event decide `youth` (`yes` / `no` / `unsure`: is it for people
about 13–25?) and 1–3 category IDs from `categories.md`. Claude does it when
`ANTHROPIC_API_KEY` is set; its reply is checked by code (JSON, known IDs,
max 3, valid `youth`), with one retry. On error or when the budget is spent,
the rule-based baseline decides instead and the event is flagged.

Routing: `youth = no` → `not_for_youth.json`; `unsure` or no category → `needs_review.json`.

## Self-consistency (stress-test repair, 9 Nov)
Each event is classified `classify.self_consistency` times (default 2). If the
answers disagree about the audience, the event goes to review (`llm_disagreement`).
If they only disagree about categories, the first answer's categories are kept
(changed after the regression run: the earlier "shared categories only" rule sent
events to review without any safety gain).

## Acceptance check
- `python -m pytest -k "parse_llm or baseline or fall_back or budget or combine or disagreement"` passes.
- `python -m eval.run_eval` reports outcome accuracy and per-category precision/recall.
- Live LLM run: done. Latest run (12 Nov) on the two human-written test sets:
  8/13 judgement events correct (baseline 2/13), no fallbacks. The final run
  for the paper comes after the demo.

## Output limit (fixed 9 Nov)
Haiku thinks before answering, and thinking counts toward the output limit. At
120 tokens some replies were cut off before any answer (`stop_reason =
max_tokens`) and the baseline silently took over. Now `max_output_tokens = 2000`
and `effort` in `config.toml`, no retry on `max_tokens`, a warning in `run_eval`
when the baseline was used, and error samples in the report.

## Warning
The baseline scores 100 % on the synthetic set, but the synthetic events and
the baseline's keywords were written by the same author (Claude). That number
says nothing about real data. See T10.
