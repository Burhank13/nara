# Architecture

## Context

One FastAPI process, one Postgres database, one React single-page app. A business has sites,
staff and shifts; a shift is a row created when someone clocks in and closed when they clock out.
There is no queue, no cache and no background worker, and that is deliberate — the load is a few
dozen people clocking in twice a day, and every part you don't add is a part that can't break at
6am in a car wash.

```
                    ┌─────────────────────────────────┐
  phone / laptop    │            React SPA            │
  ───────────────▶  │  screens · TanStack Query       │
                    └───────────────┬─────────────────┘
                                    │  fetch, everything under /api
                    ┌───────────────▼─────────────────┐
                    │            FastAPI              │
                    │  middleware  security headers,  │
                    │              request ids        │
                    │  routes      validate, delegate │
                    │  services    the business rules │
                    │  models      SQLAlchemy         │
                    └───────────────┬─────────────────┘
                                    │
                    ┌───────────────▼─────────────────┐
                    │          PostgreSQL 16          │
                    │  timestamptz · native enums     │
                    │  partial unique indexes         │
                    └─────────────────────────────────┘
```

Routes are thin on purpose: they validate input, call a service, and shape the response. If you
are looking for a rule — can this person do that, is this shift too far from the shop, what does
this week cost — it is in `app/services/`.

## Key decisions

### Everything the API answers lives under `/api`

`/overview`, `/team` and `/timesheets` are both endpoints and pages of the SPA. Without a prefix
the endpoint wins and a deep link returns JSON to someone who expected the app. The prefix is
applied in one place on the server ([`main.py`](../backend/app/main.py)) and one place in the
client ([`lib/api.ts`](../frontend/src/lib/api.ts)), so call sites never repeat it.

### One origin in production

The Docker image serves the built frontend from the API process. That keeps the refresh cookie
`SameSite=lax`, takes CORS out of the request path, and means there is one URL to configure
rather than two that must agree. In development the Vite dev server proxies `/api` to
`localhost:8000` to reproduce the same single-origin shape.

### Access token in memory, refresh token in an HttpOnly cookie

The access token lives in a JavaScript variable and dies with the tab, so XSS cannot read a token
out of `localStorage`. The refresh token is an HttpOnly cookie scoped to `path=/api/auth`, so it
is not attached to every other request. The client refreshes transparently on a 401 and retries
once.

Sessions are revoked with a `token_version` claim: bump the column, and every token already
issued for that user stops validating. That is what a password reset does, because the reason
people reset a password is usually that somebody else is signed in.

### The database enforces what matters

Where a read-then-write check would race, the constraint is in Postgres instead:

- **One open shift per person** — a partial unique index on `shifts (user_id) WHERE status = 'open'`.
  Two taps of "start shift" cannot both win.
- **Seat limits** — counted under `SELECT … FOR UPDATE` on the business row, so two invites
  accepted at once cannot both take the last seat.
- **Zone radius, latitude, longitude** — `CHECK` constraints, not just Pydantic validators.
- **Payroll codes** — unique per business.

### Account state is derived, never scheduled

A trial that ended yesterday is read-only today because
[`effective_status()`](../backend/app/services/billing.py) compares `trial_ends_at` to now on
every request — not because a nightly job moved it. Same for the past-due grace period. There is
no cron, so there is no "the cron didn't run" failure mode, and no window where the database
disagrees with reality.

Writable statuses are `trialing`, `active` and `past_due`. A failed payment is a grace period,
not a lockout: the shop keeps working for 7 days.

### Times are stored in UTC and reasoned about in the business timezone

Every timestamp column is `timestamptz`. "This week" is computed with `zoneinfo` against the
business's own timezone, so a fortnight boundary lands where the owner thinks it does and daylight
saving doesn't silently move it. Shift edits are submitted as local wall-clock times and converted
on the way in.

### Money rounds half-up

Payroll uses `ROUND_HALF_UP`, not Python's default banker's rounding. These are wages: 7.125
hours has to land on 7.25, and consistently rounding .5 to even would underpay people over time.

## Data model

```
businesses ──┬── users ──┬── shifts ──── shift_edits
             │           │
             │           └── availability
             └── locations ──┘ (a shift records which zone matched)
```

| Table | Notes |
|---|---|
| `businesses` | Name, ABN, timezone, status, seat limit, trial and past-due timestamps, Stripe ids (unused so far). |
| `users` | Everyone: owners, managers, employees. `role` and `status` are native Postgres enums. Holds the invite token hash, reset token hash, `token_version`, and the login lockout counters. Email is globally unique. |
| `locations` | A shop zone: coordinates plus a radius. Soft-deleted with `is_active`. |
| `shifts` | Start and end time, and for each the coordinates, GPS accuracy and distance from the zone. Keeping the accuracy is what lets the app explain a refusal, and lets an owner see that a shift started from 90 m away. |
| `shift_edits` | Append-only. Previous and new times, who changed them, and a required reason. Never updated, never deleted. |
| `availability` | One row per person per weekday, unique on that pair. |

Multi-tenancy is by `business_id`, checked in the dependency layer
([`deps.py`](../backend/app/deps.py)) rather than trusted from the request.

## Request flow: clocking in

1. The browser asks for a position. It only gets one on a secure origin — HTTPS or `localhost`.
2. `POST /api/shifts/start` with latitude, longitude and accuracy.
3. `get_current_user` decodes the access token, checks `token_version`, and loads the user.
4. `require_writable_business` refuses if the account is read-only or suspended.
5. The accuracy is checked first — a fix worse than 100 m is refused with `gps_inaccurate`, because
   a laptop locating itself by Wi-Fi is often hundreds of metres out and would otherwise "pass"
   the geofence from the next suburb.
6. [`check_zones`](../backend/app/services/geofence.py) finds the nearest zone containing the
   point, or the nearest zone overall. Outside it: `outside_zone`, with the distance attached so
   the UI can say how far.
7. The insert either succeeds or trips the partial unique index, which surfaces as
   `shift_already_open`.

Ending a shift is allowed from anywhere — people walk to the bus stop before they remember — but
the end location and distance are recorded.

## Errors

Every failure is `{"detail": {"code": "...", "message": "...", ...}}`. The `code` is stable and
machine-readable so the UI can branch on it; the `message` is written to be shown to a person as
it is. Extra keys carry facts the UI needs to explain the refusal, like `distance_m` on
`outside_zone`. See [api.md](api.md#error-codes).

Unhandled exceptions return a generic 500 carrying a `request_id` and never a stack trace. The
same id is on the log line, and on the Sentry event as a tag — so a support message quoting
the id someone saw on screen leads straight to the crash.

The tag is applied at the *start* of the request, not where the crash is caught. Sentry
reports an exception the first time it sees it, and that is the `logger.exception` call
inside the handler — tagging afterwards would be too late, and adding a second
`capture_exception` there is silently deduplicated rather than being a second alert.

## Frontend

React 19, Vite, Tailwind v4, react-router and TanStack Query. One responsive app for every role —
the owner gets a sidebar on a desktop and bottom tabs on a phone, driven by the `NAV` table in
[`App.tsx`](../frontend/src/App.tsx), which also decides which routes each role can reach.

Server state is TanStack Query; there is no client state library, because there is barely any
client state. The design is mobile-first, and the Playwright suite runs every test at a 390 px
viewport asserting the page never scrolls sideways — that check has caught real layout bugs twice,
both times a grid item's default `min-width: auto` letting long content widen its track.

## What isn't here

No Stripe calls — the account states and seat limits are real, but nothing charges a card. No
background jobs, no websockets (the live board polls), no map picker for zones, no service worker,
no admin console.
