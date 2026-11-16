# Source record format (inspired by Kulturnett Innlandet)

**Status: this is our own format.** Kulturnett Innlandet was dropped as a
source on 12 Nov 2026 because of legal uncertainty (see
`tasks/T08-kulturnett-dropped.md`); the project uses none of their data. The
format is *inspired by* what their public "Hva skjer" calendar shows for each
event (title, date and time, place, municipality, category, description, link).

The synthetic generator (`harness/sources/synthetic.py`), the test sets in
`fixtures/testing/` and files from organizations use this format, and
`normalize()` in `harness/sources/kulturnett.py` converts it to the internal
event format. A new real source would get its own module in `harness/sources/`
that maps its records to this format (or straight to the internal one).

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
