# Spec

**Written alongside Claude, based on discussions between groupmates. Last updated 12 Nov 2026.**


## Problem

Hamar municipality has stated the rise of loneliness amongst the youth to be a part of their main challenge. (Oversikt over folkehelsen 2023, kunnskapsgrunnlag)
We believe that a lack of knowledge greatly exacerbates this problem. 
Events are spread across ticketing sites, organization websites and posters, and nobody keeps a single overview aimed at youth. 
Keeping such an overview by hand is recurring work every week.

The Hamar region already has a shared event calendar ("Hva skjer", run by Kulturnett Innlandet) with over 1000 events, 
but it is aimed at everyone, and the entire county, so youth activities are mixed in with everything else, everywhere. 
Our workflow runs on synthetic events whose format is inspired by said calendar, plus files from any potential future organizations. It 
checks that each event has the required information, removes duplicates, decides whether it is for young people, 
sorts it into categories (music, sports, gaming, …) and, after a person approves, publishes the youth events as a filterable calendar, 
one subscribable ics feed per category and a weekly digest in Norwegian.

The goal is to make a solution that does not involve user accounts or personal data: People "follow" a category by subscribing to its feed in their own calendar app.


## Users

- **Young people in Hamar (about 13–25)** looking for something to do with others.
- **The person approving each run**, e.g. someone at a youth house or the
  municipality's culture office. Reviews the staged run before it is published,
  and can take a published event down again (`python -m harness unpublish`) if
  it turns out to be a mistake.
- **Organizations** that arrange youth activities. They can send their events
  as a file (e.g. by email); a person puts it in `fixtures/inbox/` and runs it
  with `python -m harness run --offline`, followed by review and approval as
  for any other run. 


## Definition of success

The workflow's output is correct when, for a run:

1. **Every published event passes the validation rules** in
   `harness/context/event_schema.md`: required fields present, https source
   link, active status, fixed date, within the run window, within the Hamar
   area. Checked by code.
2. **Every event that breaks a rule is rejected with the right reason.**
   Checked by code against a test set with known expected outcomes.
3. **No duplicates** (same normalized title, date and venue). Checked by code.
4. **Every published event has 1–3 categories from the allowed list**, and the
   categories match hand-made labels. Measured as precision/recall per category on the test set.
4b. **Events for other audiences are not published**, and unclear ones go to a human.
   Measured as outcome accuracy against labelled test events (`python -m eval.run_eval`).
5. **No emails or phone numbers** appear in published output. Checked by code.
6. **Nothing is published without human approval**, and a run with more than
   50 % invalid events is halted. Checked by tests.
7. **A published event can be taken down by a person**, and later runs and
   approvals don't publish it again (matched by ID, or by title, date and
   venue). Checked by tests.

Status (12 Nov 2026):

- **Criteria 1, 2, 3, 5, 6 and 7** are checked by `python -m pytest` on synthetic
  data. The web page has its own tests (`tests/test_web.py`): it shows only
  approved events and no emails or phone numbers. Unpublishing is tested in
  `tests/test_unpublish.py`. Stress test 2 (`python -m eval.stress_source`)
  fed the pipeline 9 kinds of broken source data and an unreachable source.
  At first, 2 cases crashed and the halt messages didn't say why. Now
  unreadable data stops with a clear message, broken records are rejected one
  by one, and every halt names its main reason. The regression run had 0
  crashes, and only the half-broken case was staged for approval.
- **Criteria 4 and 4b** are measured by `python -m eval.run_eval` on two
  human-written test sets (one per group member, 13 events that need
  judgement). The 22 synthetic events are not used for this, because they were
  written together with the baseline classifier.
  - Claude Haiku got the expected outcome on 8 of 13 judgement events; the
    keyword baseline on 2 of 13. Events decided by code rules: 8 of 8 for both
    (9 Nov).
  - Stress test 1 ran each test set 5 times: some answers change between
    runs. The model is now asked twice, and an event goes to review when the
    two answers disagree about the audience. Final run on test set 2: mean
    4.2 of 7. No harmful event was published in any run.
  - One event was published against its label in the 9 Nov runs: a trampoline
    park, labelled not for youth.
  - The test sets are small, so these numbers are indications. They will be
    updated after the final evaluation run.
