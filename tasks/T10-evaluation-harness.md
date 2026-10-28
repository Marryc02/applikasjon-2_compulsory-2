# T10 · Evaluation harness (for the exam)

**Status:** first version done (`eval/run_eval.py`); test set needs work.

## Done
`python -m eval.run_eval [--classifier baseline|llm]` runs the pipeline on the
labelled fixture and reports outcome accuracy (mechanical vs. judgement) and
per-category precision/recall, saved to `out/eval/`.

## Still to do
- **Independent labels.** The 22 synthetic events and their labels were written
  by Claude, together with the baseline's keywords, so the baseline's 100 % is
  not a real measurement. Write a second set of events and labels yourselves
  (humans), without looking at the keyword lists, and evaluate on that.
- More boundary cases (e.g. events exactly at the 60-day limit, odd time formats).
- Compare LLM vs. baseline on the human-written set.
- Stress tests for two perturbation classes (e.g. prompt injection in event
  text, source outage or format change), each with failure, repair and regression run.

## Acceptance check
- One command runs the full evaluation and writes a results file. ✔ (first version)
