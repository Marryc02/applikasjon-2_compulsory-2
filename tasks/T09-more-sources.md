# T09 · More sources (optional)

**Status:** not started. Ideas for after the exam. For now, organizations send
a file that a person runs with `--offline` (`fixtures/inbox/`, see T11).

## Ideas
- **Brønnøysundregistrene (open API, no key):** voluntary organizations
  registered in Hamar (kommunenummer 3403) with activity categories. Use to
  check that an event's organizer is a real organization, or to find youth
  organizations to ask for feeds. Do **not** use the `/roller` endpoint
  (lists people by name).
- **iCal/RSS feeds** that individual organizations publish for machines.
- **Organizer submissions:** text or poster PDF dropped into a folder; an LLM
  stage extracts the fields, then the existing stages take over.

## Acceptance check (to refine)
- Each new source has a normalizer to the event schema, a fixture, and tests.
