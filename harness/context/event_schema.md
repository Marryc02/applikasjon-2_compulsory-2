# Event record (internal format)

Every source is converted to this format by its normalizer
(`harness/sources/kulturnett.py`). All later stages only see this format.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `<source>:<source id>`, e.g. `kn:12345` |
| `source` | string | yes | `kulturnett` |
| `source_url` | string | yes | Link back to the original listing. Must be `https://` |
| `title` | string | yes | |
| `start` | string | yes | ISO 8601 with offset, Europe/Oslo time, e.g. `2026-11-05T19:00:00+01:00` |
| `all_day` | bool | yes | True for all-day events (start is midnight) |
| `status` | string | yes | `active`, `cancelled`, `postponed` or `unknown` |
| `venue_name` | string | yes | |
| `address` | string | no | |
| `kommune` | string | yes | Municipality, used for the area check |
| `lat`, `lon` | number | no | For a map later; not used for validation |
| `organizer` | string | no | |
| `price` | string | no | As given by the source, e.g. `Gratis`, `50 kr` |
| `source_categories` | list of strings | no | Categories as given by the source (hints only) |
| `description` | string | no | Max 300 characters. Emails and phone numbers are removed |
| `categories` | list of strings | after classify | IDs from `categories.md` |
| `youth` | string | after classify | `yes`, `no` or `unsure`: is this event for young people (about 13–25)? |
| `flags` | list of strings | no | Notes from the pipeline, e.g. `pii_removed`, `classified_by_baseline` |

## Validation rules (checked by code, `harness/validate.py`)

An event is **rejected** if any of these hold:

- `missing_field:<name>`: a required field is empty
- `invalid_url`: `source_url` is not an `https://` URL
- `status_not_active`: status is not `active` (cancelled, postponed, unknown)
- `in_past`: starts before the run time (all-day events: before today)
- `too_far_ahead`: starts more than `window.days_ahead` days after the run time
- `outside_area`: `kommune` is not in `area.kommuner` (the "Hamar-området" of the
  Hva skjer calendar: Hamar, Løten, Ringsaker, Stange)

Duplicates (same normalized title + date + venue) are removed and logged separately.

## After classification

- `youth = no` → `not_for_youth.json` (valid event, just not for our audience)
- `youth = unsure`, or no valid category → `needs_review.json` (a human decides)
- otherwise → published after approval
