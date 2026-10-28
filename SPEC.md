# Spec

> **DRAFT written by Claude, based on our discussion. Rewrite in your own words
> before submitting.** Log what you changed in `docs/prompt-log.md`.

## Problem

Young people in Hamar who feel lonely often don't know what low-threshold
social activities exist. Events are spread across ticketing sites, organization
websites and posters, and nobody keeps one overview aimed at youth. Keeping
such an overview by hand is recurring work every week.

The workflow automatically collects youth-relevant events in the Hamar area from
official machine-readable sources (APIs, RSS/iCal feeds, and later material
organizers submit themselves), checks that each event has the required
information, removes duplicates, sorts events into categories (music, sports,
gaming, …) and, after a person approves, publishes them as a filterable
calendar, one subscribable iCal feed per category and a weekly digest in Norwegian.

No user accounts and no personal data: people "follow" a category by subscribing
to its feed in their own calendar app.

## Users

- **Young people in Hamar (about 13–25)** looking for something to do with others.
- **The person approving each run**, e.g. someone at a youth house or the
  municipality's culture office. Reviews the staged run before it is published.
- **Organizations** that arrange youth activities (later: by submitting events).

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
5. **No emails or phone numbers** appear in published output. Checked by code.
6. **Nothing is published without human approval**, and a run with more than
   70 % invalid events is halted. Checked by tests.

Walking-skeleton status: criteria 1, 2, 3, 5 and 6 are checked by `python -m pytest`
on synthetic data; criterion 4 is checked against expected labels for 5 events only.
