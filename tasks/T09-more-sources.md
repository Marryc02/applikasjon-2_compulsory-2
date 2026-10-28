# T09 · More sources: RSS/iCal feeds and organizer submissions

**Status:** TODO (planning)

## Goal
Ticketmaster mostly lists large ticketed events. Add youth-focused sources:
- Official RSS or iCal feeds from Hamar organizations (only feeds the site
  offers for machines; no scraping). Record each in the README source table.
- Organizer submissions: an organization drops a text announcement or poster PDF
  into an inbox folder; an LLM stage extracts the event fields, then the
  existing validate → classify → approve stages handle it.

## Acceptance check (to refine)
- Each new source has a normalizer to the event schema, a fixture, and tests.
- A submission missing time or place is rejected with the right reason.
