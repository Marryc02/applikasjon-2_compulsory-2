# T07 · Kill switch and budgets

**Status:** done (first version)
**Code:** `harness/pipeline.py`, `harness/classify.py` · **Settings:** `config.toml`

## Goal
- Kill switch: if more than `safety.max_reject_ratio` of fetched events fail
  validation, or fewer than `min_events_fetched` are fetched, halt: nothing is
  staged for approval, exit code 2.
- Budget: at most `classify.max_llm_calls` calls and `classify.max_total_tokens` tokens per run.
- Nightly CI job has a 10-minute timeout.

## Acceptance check
- `python -m pytest -k "kill_switch or budget"` passes.

## Open question
Is 70 % the right threshold? Decide after seeing real data (T08).
