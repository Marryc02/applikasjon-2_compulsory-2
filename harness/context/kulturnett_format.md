# Kulturnett Innlandet record format (ASSUMED)

**Status: we have requested API access from Kulturnett Innlandet
(kulturnett@innlandetfylke.no) but have not received it. This format is our
own assumption**, based on what the public "Hva skjer" calendar shows for each
event (title, date and time, place, municipality, category, description, link).

The synthetic generator (`harness/sources/synthetic.py`) produces records in
this format, and `harness/sources/kulturnett.py` converts them to the internal
event format. When the real API documentation arrives:

1. Save a real response to `fixtures/` (no personal data).
2. Update `normalize()` in `harness/sources/kulturnett.py` to map the real
   fields. Nothing after the normalize stage should need to change.
3. Implement `fetch_live()`.
4. Record the decision in a meeting report and in `docs/prompt-log.md` if the agent helped.

## Assumed record

```json
{
  "id": "12345",
  "tittel": "Konsert med ungdomsband",
  "beskrivelse": "Kort tekst om arrangementet.",
  "start": "2026-11-05T19:00:00+01:00",
  "heldags": false,
  "sted": {
    "navn": "Hamar kulturhus",
    "adresse": "Torggata 100",
    "postnummer": "2317",
    "kommune": "Hamar",
    "lat": 60.7949,
    "lon": 11.0669
  },
  "kategorier": ["Konsert", "Ungdom"],
  "arrangor": "Hamar kulturhus",
  "pris": "Gratis",
  "url": "https://kulturnett.innlandetfylke.no/hva-skjer/12345",
  "status": "publisert"
}
```

- `start`: ISO 8601. For all-day events (`heldags: true`) only a date, e.g. `"2026-11-05"`.
- `status`: `publisert`, `avlyst` (cancelled) or `utsatt` (postponed).
- `sted` may be missing or incomplete.
- A response is a JSON object with an `events` list (or just a list).

Fields starting with `_` (e.g. `_expected` in synthetic data) are **not** part of
the format. They are test labels and are dropped before any stage sees them.
