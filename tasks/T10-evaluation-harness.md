# T10 · Evaluation harness (for the exam)

**Status:** TODO (later)

## Goal
A repeatable evaluation run over a fixed test set, reporting numbers:
- Test set: typical, boundary and must-reject cases (`eval/`), with expected outcomes.
- Code checks: schema, dates, links, area, rejections.
- Classification: precision/recall per category against hand-made labels;
  LLM vs. baseline.
- Stress tests for two perturbation classes (e.g. prompt injection in event
  text, API outage/rate limiting), each with failure, repair and regression run.

## Acceptance check
- One command runs the full evaluation and writes a results file.
