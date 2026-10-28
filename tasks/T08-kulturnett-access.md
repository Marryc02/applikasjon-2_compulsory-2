# T08 · Get Kulturnett Innlandet API access (humans)

**Status:** TODO: request not sent yet

## Steps
1. Email kulturnett@innlandetfylke.no: who we are, what the service does
   (youth events in the Hamar area, non-commercial, links back, no personal
   data), and ask for API/feed access and its documentation and terms.
2. Log the request and the answer in a meeting report.
3. When access is granted:
   - Save one real response to `fixtures/kulturnett_<date>_REAL.json`.
   - Update `normalize()` and implement `fetch_live()` in `harness/sources/kulturnett.py`.
   - Update `harness/context/kulturnett_format.md` from "ASSUMED" to the real format.
   - Fill in the Kulturnett row of the source table in `README.md`.
4. If access is refused: decide in a meeting whether to continue on synthetic
   data only (allowed by the course brief) or add other sources (T09).

## Acceptance check
- `python -m harness run --source kulturnett` collects real events, and
  `python -m harness run --offline fixtures/<real file>` reproduces the run.
