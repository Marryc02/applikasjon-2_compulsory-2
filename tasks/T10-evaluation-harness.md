# T10 · Evaluation harness (for the exam)

**Status:** first version done (`eval/run_eval.py`); test set needs work.

## Done
`python -m eval.run_eval [--classifier baseline|llm]` runs the pipeline on the
labelled fixture and reports outcome accuracy (mechanical vs. judgement) and
per-category precision/recall, saved to `out/eval/`.

- Labels are checked before every run (`--check-only` to check without running).
- `--repeat N` runs a fixture N times and lists events whose result changed (model variance).
- Human-written test sets: `fixtures/kulturnett_HUMAN_*.json`, one per group member.
  Classifier on these 13 judgement events: baseline 2/13, LLM 8/13 (9 Nov, one run each).

## Still to do
- ~~Independent, human-written labels~~ (done, see above).
- More boundary cases (e.g. events exactly at the 60-day limit, odd time formats).
- ~~Compare LLM vs. baseline on the human-written set~~ (done, see above).
- Run `--repeat 5` with the LLM on both human sets (model-variance stress test).
- Stress tests for two perturbation classes (e.g. prompt injection in event
  text, source outage or format change), each with failure, repair and regression run.

## Acceptance check
- One command runs the full evaluation and writes a results file. ✔ (first version)
