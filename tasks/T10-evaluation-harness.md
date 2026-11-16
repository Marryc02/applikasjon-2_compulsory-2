# T10 · Evaluation harness (for the exam)

**Status:** done (`eval/run_eval.py`). Results in `docs/results/`; the final run
for the paper comes after the demo.

## Done
`python -m eval.run_eval [--classifier baseline|llm]` runs the pipeline on the
labelled fixture and reports outcome accuracy (mechanical vs. judgement) and
per-category precision/recall, saved to `out/eval/`.

- Labels are checked before every run (`--check-only` to check without running).
- `--repeat N` runs a fixture N times and lists events whose result changed (model variance).
- Human-written test sets: `fixtures/testing/kulturnett_HUMAN_*.json`, one per group member.
  Classifier on these 13 judgement events: baseline 2/13, LLM 8/13 (9 Nov, and
  again in a check run on 12 Nov). Code checks 8/8.

## Still to do
- ~~Independent, human-written labels~~ (done, see above).
- More boundary cases (e.g. events exactly at the 60-day limit, odd time formats). Not done.
- ~~Compare LLM vs. baseline on the human-written set~~ (done, see above).
- ~~Run `--repeat 5` with the LLM on both human sets~~ (done: stress test 1,
  model variance, 9 Nov. Repair: ask twice; regression in `docs/results/`).
- ~~Stress tests for two perturbation classes~~ (done: stress test 1, model
  variance; stress test 2, dependency failure with `eval/make_stress_inputs.py`
  and `eval/stress_source.py`, 12 Nov).

## Acceptance check
- One command runs the full evaluation and writes a results file. ✔
- `python -m eval.stress_source` runs stress test 2 and reports 0 crashes. ✔
