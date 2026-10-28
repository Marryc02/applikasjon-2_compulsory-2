# T01 · Collect events from the Ticketmaster API

**Status:** done (offline). Not yet run against the live API.
**Code:** `harness/fetch_ticketmaster.py`

## Goal
Fetch upcoming events within `area.radius_km` of Hamar for the next
`window.days_ahead` days from the Ticketmaster Discovery API, and save the raw
response to `out/raw/<run_id>.json` in the API's own format.

## Constraints
- API key only from the environment (`TICKETMASTER_API_KEY`); never in logs or error messages.
- Retry on HTTP 429 and 5xx (max `max_retries`), stop at `max_events`.
- `--offline <file>` replays a saved response with no network.

## Acceptance check
- `python -m harness run --offline` prints `[1 collect]   12 events`.
- `python -m pytest` passes.
- Live: see T08.
