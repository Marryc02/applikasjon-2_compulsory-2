# Event record (internal format)

Every source is converted to this format by the normalize stage. All later
stages only see this format.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `<source>:<source id>`, e.g. `tm:Z698xZ...` |
| `source` | string | yes | `ticketmaster` (more sources later) |
| `source_url` | string | yes | Link back to the original listing. Must be `https://` |
| `title` | string | yes | |
| `start` | string | yes | ISO 8601 with offset, Europe/Oslo time, e.g. `2026-11-05T19:00:00+01:00` |
| `date_tbd` | bool | yes | True if the source says the date is not decided |
| `status` | string | yes | Source status. Allowed: `onsale`, `offsale`, `rescheduled` |
| `venue_name` | string | yes | |
| `address` | string | no | |
| `city` | string | yes | |
| `lat`, `lon` | number | no | Used for the area check when present |
| `price_min`, `price_max` | number | no | |
| `currency` | string | no | |
| `age_restricted` | bool | no | Legal age limit enforced at the door |
| `source_categories` | list of strings | no | Categories as given by the source (hints only) |
| `description` | string | no | Max 300 characters. Emails and phone numbers are removed |
| `categories` | list of strings | yes (after classify) | IDs from `categories.md` |
| `flags` | list of strings | no | Notes from the pipeline, e.g. `pii_removed`, `classified_by_baseline` |

## Validation rules (checked by code, `harness/validate.py`)

An event is **rejected** if any of these hold:

- `missing_field:<name>`: a required field is empty
- `invalid_url`: `source_url` is not an `https://` URL
- `status_not_active`: status is cancelled, postponed or unknown
- `date_tbd`: no fixed date
- `in_past`: starts before the run time
- `too_far_ahead`: starts more than `window.days_ahead` days after the run time
- `outside_area`: more than `area.radius_km` from Hamar centre (or, without
  coordinates, a city not in `area.allowed_cities`)

Duplicates (same normalized title + date + venue) are removed and logged separately.
Events with no category after classification go to **needs_review**, not to rejected.
