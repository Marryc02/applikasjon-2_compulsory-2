# T01 · Collect events (Kulturnett Innlandet, simulated for now)

**Status:** simulated source done. Live source waiting for API access (T08).
**Code:** `harness/sources/` · **Format:** `harness/context/kulturnett_format.md` (ASSUMED)

## Goal
Collect upcoming events in the Hamar area. Until Kulturnett Innlandet gives us
API access, `harness/sources/synthetic.py` simulates their feed: 22 made-up
events per run in the assumed format, with dates relative to the run time and an
`_expected` label on each (the outcome a correct pipeline should produce).
Every run saves what it collected to `out/raw/<run_id>.json`.

## Acceptance check
- `python -m harness run` prints `[1 collect]   22 events from synthetic (simulated Kulturnett feed)`.
- `python -m harness run --source kulturnett` exits with code 3 and the message
  "API access has not been granted yet" (no crash).
- `python -m pytest -k "synthetic or fixture_matches"` passes.
