# T07 · Kill switch and budgets

**Status:** done
**Code:** `harness/pipeline.py`, `harness/classify.py` · **Settings:** `config.toml`

## Goal
- Kill switch: if more than `safety.max_reject_ratio` (50 %) of collected events
  fail validation, or nothing is collected, halt: nothing is staged, exit code 2.
  The message names the most common reason and a likely cause, e.g. "The
  source may have changed its format" (stress test 2, repair R3).
- Budget: at most `classify.max_llm_calls` calls and `classify.max_total_tokens` tokens per run.
- Nightly CI job has a 10-minute timeout.

## Acceptance check
- `python -m pytest -k "kill_switch or budget"` passes.

## Decision: keep 50 % (12 Nov)
The threshold was 70 % in the Compulsory 2 plan and is 50 % now. In stress
test 2 we considered lowering it (R4) and decided not to: the half-broken case
is still staged, its valid events are fine, and a person must approve them
anyway. A lower limit would give more false alarms.
