# White paper notes

Things to remember when writing the final paper (due 3 Dec 2026, 11:59).
Add to this list as we go.

## Safe operation
- **Cost is capped twice:** per run in the code (`config.toml`: max 100 LLM
  calls and 150,000 tokens per run, then the keyword baseline takes over) and
  per month on the Anthropic account (spend limit / prepaid credits without
  auto-reload).
- **Secrets:** API key only in `.env`; `.gitignore` covers `.env` and
  `.env.*` (but keeps `.env.example`), tested; Claude Code is denied reading
  `.env`; we checked the git history for keys (`git log -p | findstr "sk-ant"`).
- **Nothing is published automatically.** Justify it: audience is young
  people; the scam and marijuana test events pass every validation
  rule, so only the human approval step stops them.
- **Kill switch:** >50 % invalid events or nothing collected → run halts.
- **Prompt injection:** event text is passed as data; the LLM's reply must
  match a strict format or it's rejected and the baseline decides (tested with
  a fake client that "obeyed" an injection).
- **Privacy:** emails and phone numbers are removed. Personal **names** are
  not: a deliberate trade-off, since performers' and speakers' names belong
  in listings. Idea: flag possible private names for review instead of rejecting.

## Evaluation findings
- **Overfitting:** the keyword baseline scores 100 % on Claude's synthetic
  events (Claude wrote both the events and the keywords) but only 2/13 on our
  human-written events. Why human-written test sets matter.
- **Report split numbers, not just accuracy:** code checks 8/8 vs. classifier
  2/13. A single accuracy number mixes the two and hides what happens.
- **"Right for the wrong reason":** the baseline gets the scam and marijuana
  events "right" (needs review) only because it sends everything to review.
- **REAL RESULT (9 Nov, after the thinking fix, no fallbacks):**

  | | Keyword baseline | Claude |
  |---|---|---|
  | Checks done in code | 8/8 | 8/8 |
  | Judgement events | 2/13 | 8/13 |
  | Test set 1 / test set 2 | 0/6, 2/7 | 4/6, 4/7 |

  Result files: `out/eval/20261109-191713-llm.json` (test set 1),
  `out/eval/20261109-191503-llm.json` (test set 2). Copy to `docs/results/`.
  Misses: Strikkekafé → review (unsure; cautious); trampoline park →
  **published although labelled not for youth** (the only publication against
  a label; harmless but a label disagreement, and it's really a price
  promotion, which no rule catches); Fønix → review (unsure, no age given);
  scam + marijuana → "not for youth" (not published, but they skip the review
  queue, so no person is asked to look at them; a design question).
  Improved vs. broken run: Powerwolf concert and BookTok now correct.
  Idea: add an "unsafe publications" count to the evaluation (here: 1, the
  trampoline park, by label).
- **Stress test 1: model variance (9 Nov), `--repeat 5`, no fallbacks in any run:**

  | | Score per run | Events that changed |
  |---|---|---|
  | Test set 1 | 4/6 ×5 | only categories of the eldremøte (social vs. social+food); outcome always correct |
  | Test set 2 | 4/7, 4/7, 4/7, 4/7, 3/7 (mean 3.8) | brettspillkveld (accepted 3/5, review 2/5), scam (not for youth 4/5, review 1/5), book club (always accepted; categories vary) |

  Result files: `20261109-193509-llm-x5_markus.json`, `20261109-193736-llm-x5_joachim.json`.
  - **A stable score can hide unstable answers:** in run 1 of test set 2 the
    score was 4/7 like the others, but different events were right/wrong.
    Report per-event stability, not just the total.
  - **Variance never changed what reached the public:** flips are between
    accepted ↔ review or not-for-youth ↔ review. Marijuana: not for youth 5/5.
    Trampoline park: the only publication against a label, 5/5. Variance costs
    reviewer time, not safety.
  - The events that wobble are the ones whose text doesn't say who it's for.
  - **Repair chosen: (A) ask twice, review on disagreement** (over B, majority
    of three, which hides the doubt, and C, accept and document). Reason: fits
    the design principle "when unsure, a human decides", and isn't tuned to
    these 13 events. Details: audience disagreement → review
    (`llm_disagreement`); category-only disagreement → keep shared categories
    (none shared → review). Cost: 2× calls (still fractions of a cent);
    `max_llm_calls` 100 → 200. Setting: `classify.self_consistency`.
  - **Regression (9 Nov, `--repeat 5`, ask twice):** set 1: 4,3,4,4,4 (was
    4×5); set 2: 2,4,3,5,4 (was 4,4,4,4,3). Unstable events: 2 + 3 (was 1 + 3).
    Scam → review 3/5 (was 1/5, matches label); brettspillkveld accepted 2/5
    (was 3/5). Harmful events published: 0 (unchanged). Files:
    `20261109-195225-llm-x5.json` (set 1), `20261109-195850-llm-x5.json` (set 2).
  - **Result: no measurable improvement in stability; more events routed to
    review.** Why: disagreement is itself random, so asking twice shifts wobbly
    events toward review instead of making them deterministic. With 13 events ×
    5 runs, 3.8 vs 3.6 is noise; don't claim "worse".
  - **Side effect of our rule (not the model):** category-only disagreement with
    no shared category (e.g. learning vs social) → "no category" → review (book
    club, 2/5). To fix either way: keep the first answer's categories instead.
  - **Decision (9 Nov): keep A.** Reason: having a human in the loop matters
    more to us than stable numbers; asking twice sends doubtful events to a
    person more often. We accept the cost (2× calls, more review work) and
    that it does not make results more stable. Together with it: on
    category-only disagreement, keep the first answer's categories (fixes the
    book-club side effect; regression test added).
  - **Final regression after the category fix (9 Nov, test set 2,
    `20261109-201558-llm-x5_joachim.json`):** scores 4,5,4,3,5 (mean 4.2).
    Book club accepted 5/5 (fix confirmed). Scam → review 4/5 (was 1/5 with
    ask-once). Brettspillkveld accepted 3/5. BookTok to review once (audience
    disagreement). Marijuana: not for youth 5/5. Harmful events published: 0.

    | Test set 2 | Ask once | Ask twice | Ask twice + category fix |
    |---|---|---|---|
    | Mean score | 3.8 | 3.6 | 4.2 |
    | Book club accepted | 5/5 | 3/5 | 5/5 |
    | Scam to review | 1/5 | 3/5 | 4/5 |
    | Harmful published | 0 | 0 | 0 |

    Wording for the paper: doubtful events reach a human more often; nothing
    harmful published; score differences are within noise (13 events × 5 runs).
    **Stress test 1 complete.**
- **Stress test 2: dependency failure (12 Nov), broken source data.**
  *Inject:* `python -m eval.make_stress_inputs` writes 9 broken versions of
  the (synthetic) source data to `fixtures/stress/` (empty, cut-off JSON, wrong
  wrapper `{"data": [...]}`, non-event records, renamed fields, Norwegian
  date text, wrong region, 64 % and 50 % missing dates); case 10 is the
  real source being unreachable. `python -m eval.stress_source` runs all 10
  with the keyword baseline (no API cost).
  *Observe (result `20261112-182001.json`):* nothing broken was ever staged,
  but 2 cases **crashed** with a Python traceback (02 `JSONDecodeError`,
  04 `AttributeError: 'str' object has no attribute 'get'`); 03 halted as
  "too_few_events_collected", which hides that the format changed; halt
  messages like "reject_ratio 1.00 > 0.5" don't say *why*. Only 09 (half
  broken) was staged, and waited for a human.
  *Repair (decided 12 Nov):*
  - R1: unreadable data (not JSON, no `events` list) stops with a plain
    message, e.g. "The source's data has no 'events' list (found: data). The
    source may have changed its format. Nothing was staged."
  - R2: a record that isn't an event is rejected on its own as
    `invalid_record` (in `rejected.json`, with a short preview run through
    the privacy filter) instead of crashing the whole run.
  - R3: the kill-switch message names the most common reason and a likely
    cause, e.g. "100% of events were rejected (limit 50%). Most common
    reason: missing_field:title (100% of events). The source may have
    changed its format."
  - R4 *not changed:* the 50 % limit. Case 09 (half the dates missing) is
    still staged, on purpose: the valid half is fine, and nothing is
    published without a human anyway. Lower limit = more false alarms.
  *Regression (my run, before yours):* 0 crashes; 02 and 03 now
  `source_unreadable` with the messages above; 04 halted with "Most common
  reason: invalid_record"; 05–08 halted with a reason; 09 still the only
  staged case; 10 unchanged. New `eval/test_stress.py` (7 tests) keeps this
  from breaking again; 88 tests total. Regression result
  `20261112-190002.json` (12 Nov, Windows): identical to the above.
  Small follow-up: the halt line in the log said "Nothing staged for
  approval" twice; fixed so it's said once. **Stress test 2 complete.**
- *Superseded (broken run, partly baseline decisions):* LLM vs. baseline on
  the same 21 human-written events (run 9 Nov 2026, one run per file, model
  `claude-haiku-5-5`):

  | | Keyword baseline | Claude (LLM) |
  |---|---|---|
  | Checks done in code | 8/8 | 8/8 |
  | Events sorted by the classifier | 2/13 | 8/13 |
  | Accuracy (test set 1 / test set 2) | 40 % / 54.5 % | 70 % / 81.8 % |

  Result files: `out/eval/20261109-164212-llm.json` (test set 1) and
  `out/eval/20261109-164350-llm.json` (test set 2). PNG summaries committed.
- **CORRECTION (9 Nov): the LLM numbers above are partly baseline numbers.**
  A later run on test set 2 showed `llm_errors: 4, fallback_used: 4`: for
  BookTok, Fønix, the scam and the marijuana event, Claude's answer was
  invalid twice, so the keyword baseline decided. These are the same events
  that went to review as "unsure, no category" in the evaluation. The
  evaluation didn't show this at the time (it now warns about it).
  So the earlier readings "Claude fails safely" and "Claude treats unsure as
  no category" were probably about the baseline, not Claude. Re-run and
  re-check before using them. Good honest-failure-reporting material.
- **Cause found (9 Nov):** all 4 failures had `stop_reason=max_tokens` and an
  empty reply. Haiku 5.5 thinks before answering, and thinking counts toward
  `max_tokens`; our limit (120, sized for a model without thinking) ran out
  before any answer, on exactly the hard events (where it thinks most).
  **Repair:** `max_output_tokens` 120 → 2000 (a ceiling, you only pay for what's
  used), effort made configurable (`medium`), no pointless retry when capped,
  per-run token budget 60k → 150k. **Regression:** re-run the LLM evaluation
  and `--repeat 5` on both test sets → these are the real LLM numbers.
  Strong stress-test story (observe → repair → regression), and a lesson:
  a silent fallback can hide a broken component inside a "good" score.
- **Some misses are label disagreements, not clear mistakes:** BookTok "for
  voksne" (18–25-year-olds are adults too), the trampoline park (teenagers are
  typical customers), Strikkekafé (not tied to an age). We debated these
  labels ourselves.
- **Powerwolf concert:** found `music` but unsure about the audience, although
  it's an open event (check whether this was Claude or the fallback).
- **Marijuana and scam → needs_review, but for a weak reason:** not because
  they were recognized as harmful (in the latest run, Claude's answer for both
  was invalid and the baseline decided). There's still no explicit
  harmful/scam check; human approval is what actually protects.
- **Small sample:** 13 judgment events, one run each. Category numbers rest
  on 1–2 events each; present them as indications. Re-run each file a few
  times to see how stable 8/13 is (= the model-variance stress test).
- **Evaluation tooling:** labels are checked before every run (clear per-event
  errors instead of crashes); `--repeat N` measures model variance.
- **Category edge:** the book club got `learning` instead of `social`;
  `categories.md` could define the boundary more clearly.

## Decisions and their reasons (also for meeting reports / prompt log)
- Dropped user accounts and followers: the brief forbids storing personal data.
- No web scraping: only APIs, RSS/iCal or submitted material.
- Ticketmaster → Kulturnett Innlandet ("Hva skjer", 1000+ events in the
  Hamar region, but not aimed at youth).
- Kulturnett didn't answer → synthetic data, **agreed with the lecturer**.
- **12 Nov: Kulturnett Innlandet dropped as a source entirely** because of
  legal uncertainty about using their data. *(Fill in the specifics.)* The
  synthetic dataset stays; its format is only *inspired by* their "Hva skjer"
  calendar and contains none of their data. README updated. For the paper:
  say plainly that the system has never run on real events, and that a real
  source (API/RSS/iCal) would be a new module in `harness/sources/`.
- *Superseded 12 Nov:* "only `harness/sources/kulturnett.py` needs to change
  when access arrives". Don't use this deployment path in the paper.
- Demo moved to week 48; plan to finish everything before the demo.

## Agent output we corrected or that failed (prompt-log material)
- **Output-token limit too low → silent fallback to the keyword baseline (9 Nov).**
  - *What happened:* Claude Code (the agent) set `max_output_tokens = 120`
    for the LLM classifier, sized for a model that answers directly. Our
    model, Claude Haiku 5.5, *thinks before answering* by default, and the
    thinking counts toward that limit. On hard events (BookTok, Fønix, the
    scam, the marijuana event) the 120 tokens were used up by thinking, so
    the reply was **empty** (`stop_reason = max_tokens`).
  - *Why we didn't notice at first:* the pipeline treats an empty/invalid
    answer as an error and lets the **keyword baseline** (no AI) decide
    instead. The evaluation only showed outcomes, not who decided, so the
    first "Claude" score (8/13) was partly baseline decisions.
  - *How we found it:* a staged run's `report.json` showed `llm_errors: 4,
    fallback_used: 4`. We added logging of the model's actual reply and the
    stop reason, which showed empty replies with `max_tokens`.
  - *Fix:* `max_output_tokens` 120 → 2000 (a ceiling; you pay only for what's
    used), effort made a setting (`medium`), no retry when the limit is hit,
    per-run token budget 60k → 150k. The evaluation now **warns** when any
    event was decided by the baseline during an LLM run.
  - *Lesson:* a silent fallback can hide a broken component inside a score
    that looks fine. Check *who* made each decision, not just the result.
    Also: check model-specific behavior (thinking) in the docs instead of
    reusing settings from older models.
- The phone-number filter missed "912 34 567." (full stop after it); found
  and fixed, test added.
- The skeleton (tested on Linux) failed on Windows: missing `tzdata`. Fixed;
  CI now runs on Ubuntu and Windows.
- Claude's own test set was meaningless as a measurement (see overfitting).

## Architecture points
- Code where possible, LLM only where judgment is needed (step 5 only).
- What the LLM sees and doesn't see (context engineering).
- Automatic: steps 1–6 every night. Manual: step 7 (approve) and needs-review.
- Be ready to defend "is it agentic?": the agent is deliberately constrained
  for safety.

- **Review in practice (9 Nov):** reviewer dropped the scam and marijuana
  events (`dropped_in_review`), marked two as not for youth, published 3.

## Known gaps to mention honestly
- **Public page = all approved runs (changed 12 Nov).** Before, each `approve`
  replaced `out/public/`, so the page showed only the last approved run.
  Now approve adds the run's events to what's already public; the same event
  (same id, or same title + date + venue) from a newer run replaces the older
  version, and events that started before today are dropped. Consequence:
  there's no command to *remove* a published event (e.g. if it's cancelled
  later); it stays until its date has passed. A person would have to edit
  `out/public/events.json` by hand.
- ~~No `review` command for the needs-review queue~~: added 9 Nov
  (`python -m harness review`; accept with categories / not for youth / drop /
  skip; every decision logged in the run's `report.json`). Good HITL point.
- The nightly run can't easily be approved (approve works on local files).
- ~~Run ID came from `--now`~~: fixed 12 Nov. A run with an old `--now` got an
  old ID, so `review`/`approve` (which pick the highest ID) opened a newer run
  instead, and two runs with the same `--now` overwrote each other. Found when
  reviewing the human test sets. The ID is now the real start time; the
  pretend time is still saved as `run_time` in `report.json`. Test added.
- No real source: only synthetic data, in a format inspired by Kulturnett.

## Related work
- koigenhamar.no: nightly collection of Hamar events from open sources; not
  aimed at youth.

## Before submitting
- Re-run the full evaluation after the last code change (raw output → appendix).
- Tag the final commit `exam`.
- Main text 7–8 pages; appendix: prompt logs, evaluation logs, ≥ 8 meeting reports.
