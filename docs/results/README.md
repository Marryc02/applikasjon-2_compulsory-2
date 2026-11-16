# Evaluation results

Raw output kept for the white paper, copied from `out/` (which git ignores).
Evaluation runs (`python -m eval.run_eval`) use run time
`2026-11-02T08:00:00+01:00`. LLM runs use `claude-haiku-5-5`.

Test set 1 and test set 2 are the two human-written fixtures in
`fixtures/testing/kulturnett_HUMAN_*.json` (13 judgement events in total: 6 + 7).
"Judgement" = events the classifier decides; "code" = rejections and
duplicates, decided by fixed rules.

| File | Classifier | Test set | Runs | What it shows |
|---|---|---|---|---|
| `20261029-180211-baseline.json` | baseline | synthetic | 1 | 100 % on Claude's own synthetic events: overfitting (Claude wrote both the events and the keyword rules) |
| `20261029-180513-baseline.json` | baseline | 1 | 1 | Code 4/4, judgement 0/6: the keyword rules fail on human-written events |
| `20261029-180738-baseline.json` | baseline | 2 | 1 | Code 4/4, judgement 2/7 (both "correct" only because everything went to review) |
| `20261109-181759-llm.json` | LLM | 2 | 1 | **Broken run:** output limit (120 tokens) too low for a thinking model; 4 events got empty replies (`stop_reason = max_tokens`) and fell back to the baseline |
| `20261109-191713-llm.json` | LLM | 1 | 1 | After the output-limit fix: judgement 4/6, no fallbacks |
| `20261109-191503-llm.json` | LLM | 2 | 1 | After the output-limit fix: judgement 4/7, no fallbacks |
| `20261109-193509-llm-x5.json` | LLM, ask once | 1 | 5 | Stress test 1 (model variance): 4/6 in every run; only categories of one event varied |
| `20261109-193736-llm-x5.json` | LLM, ask once | 2 | 5 | Stress test 1: 4, 4, 4, 4, 3; three events changed outcome between runs |
| `20261109-195225-llm-x5.json` | LLM, ask twice | 1 | 5 | Repair (option A), regression: 4, 3, 4, 4, 4 |
| `20261109-195850-llm-x5.json` | LLM, ask twice | 2 | 5 | Repair, regression: 2, 4, 3, 5, 4; side effect: book club sent to review with "no category" |
| `20261109-201558-llm-x5.json` | LLM, ask twice + category fix | 2 | 5 | Final regression: 4, 5, 4, 3, 5 (mean 4.2); book club accepted 5/5; scam to review 4/5; nothing harmful published |

Stress test 2 (dependency failure, `python -m eval.stress_source`; 9 broken
inputs + an unreachable source, keyword baseline):

| File | What it shows |
|---|---|
| `20261112-182001.json` | Observe: 2 crashes (02 not JSON, 04 garbage records), 03 halted with a misleading reason, halt messages without a cause. Only 09 (half broken) staged |
| `20261112-190002.json` | Regression after repairs R1–R3: 0 crashes, every halt names its main reason, only 09 staged |
| `20261112-220849.json` | Rerun on the 12 Nov code (after all fixes): same as the regression, 0 crashes, only 09 staged |

Check run after all fixes (12 Nov, Claude Haiku, no fallbacks). Not the final
run; that comes after the demo:

| File | Classifier | Test set | Runs | What it shows |
|---|---|---|---|---|
| `20261112-220639-llm.json` | LLM, ask twice | synthetic | 1 | Code 8/8, judgement 14/14. Not a fair test: Claude wrote these events |
| `20261112-220719-llm.json` | LLM, ask twice | 1 | 1 | Code 4/4, judgement 3/6 |
| `20261112-220756-llm.json` | LLM, ask twice | 2 | 1 | Code 4/4, judgement 5/7; trampoline park published against its label |
| `20261112-221637-report.json` | LLM | synthetic | 1 | Full program run (`python -m harness run`): 22 collected, 7 rejected, 1 duplicate, 10 accepted; 28 LLM calls, ~30 000 tokens |

Summary: code checks 8/8 in every run. Classifier on the 13 judgement events:
baseline 2/13, Claude 8/13 (single runs, 9 Nov and 12 Nov). The final evaluation run
after the demo will be added here. Harmful test events (scam, marijuana)
were never published in any run.
