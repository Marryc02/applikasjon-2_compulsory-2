# T07 · Kill switch and budgets

**Status:** done (first version)
**Code:** `harness/pipeline.py`, `harness/classify.py` · **Settings:** `config.toml`

## Goal
- Kill switch: if more than `safety.max_reject_ratio` (50 %) of collected events
  fail validation, or nothing is collected, halt: nothing is staged, exit code 2.
- Budget: at most `classify.max_llm_calls` calls and `classify.max_total_tokens` tokens per run.
- Nightly CI job has a 10-minute timeout.

## Acceptance check
- `python -m pytest -k "kill_switch or budget"` passes.

## Open question
Is 50 % the right threshold for real Kulturnett data? Decide when we have it (T08).
