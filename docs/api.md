# API reference

Base path is `/api`. Interactive docs generated from the code are at `/docs` when the server is
running — this page covers the parts the schema can't tell you: how auth works, what the error
codes mean, and which role can call what.

## Authentication

Sign in returns an **access token** in the JSON body and sets a **refresh token** as an HttpOnly
cookie:

```
nara_refresh=<jwt>; HttpOnly; Path=/api/auth; SameSite=lax; Max-Age=2592000
```

Send the access token as `Authorization: Bearer <token>`. It lasts 60 minutes. When it expires,
`POST /api/auth/refresh` (which needs only the cookie) returns a new one. The web client does
this transparently on a 401 and retries the request once.

Tokens carry a `tv` (token version) claim checked against the user's `token_version` column.
Bumping that column invalidates every token already issued for that user — which is what a
password reset does.

After 8 failed sign-ins an account is locked for 15 minutes. The counter is committed even though
the request fails, so a rollback can't hand an attacker unlimited guesses.

### `POST /api/auth/signup` → 201

Creates a business and its owner. Starts a 14-day trial with 10 seats.

```json
{
  "business_name": "Sparkle Car Wash",
  "full_name": "Olivia Owner",
  "email": "olivia@sparklewash.com",
  "password": "at-least-ten-characters",
  "timezone": "Australia/Sydney"
}
```

Returns `{ access_token, token_type, user, business }`.

Passwords must be at least 10 characters. The upper bound is bcrypt's 72 **bytes**, checked
explicitly rather than silently truncated.

### `POST /api/auth/login` → 200

`{ "email": "...", "password": "..." }`. Same response shape as signup.

### `POST /api/auth/refresh` → 200

No body. Reads the cookie, returns a fresh access token.

### `POST /api/auth/logout` → 204

Clears the cookie.

### `GET /api/auth/me` → 200

`{ user, business }` for the current token.

### Password reset

| Endpoint | Notes |
|---|---|
| `POST /api/auth/forgot-password` | `{ "email": "..." }`. **Always** 204, whether or not the address exists — this endpoint must not reveal who has an account. An invited user who never set a password gets nothing; their invite is the way in. |
| `GET /api/auth/reset/{token}` | Previews the account so the reset screen can say whose it is. 404 if the token is used, expired or invented. |
| `POST /api/auth/reset-password` | `{ "token": "...", "password": "..." }` → 204. Sets the password, burns the token, revokes every session, and clears any lockout. |

Only a hash of the token is stored, so a database leak doesn't hand over working reset links.
Links expire in an hour and work once.

## Invites

| Endpoint | Role | Notes |
|---|---|---|
| `GET /api/invites/{token}` | public | Preview: business name, who invited you, the email it was sent to. |
| `POST /api/invites/{token}/accept` | public | `{ "full_name": "...", "password": "..." }` → a signed-in session. |

Invites expire in 7 days. A pending invite holds a seat until it does.

## Team — owner only

| Endpoint | Notes |
|---|---|
| `GET /api/team` | Members plus seat usage. |
| `POST /api/team/invites` | `{ email, full_name, role }` where role is `employee` or `manager` → 201 with `{ member, invite_url, seats }`. The `invite_url` is built from `APP_BASE_URL`. If a key is configured the invite is also emailed; if not, the link is logged. |
| `PATCH /api/team/members/{id}` | `{ "payroll_code": "EMP001" }`, or `null` to clear it. Unique per business. |
| `POST /api/team/members/{id}/resend` | New token, new 7-day expiry. |
| `DELETE /api/team/members/{id}` | Revokes an invite that was never accepted. |
| `POST /api/team/members/{id}/archive` | Frees the seat. The owner cannot be archived. |
| `POST /api/team/members/{id}/restore` | Takes a seat again, so it can fail with `seat_limit_reached`. |
| `GET /api/team/seats` | `{ used, limit, available }`. |

A seat is one active employee or manager, or an unexpired invite. **Owners are free.**

## Locations (shop zones) — owner only

`GET`, `POST`, `PATCH /{id}`, `DELETE /{id}` on `/api/locations`.

```json
{ "name": "Harbour St", "address": "...", "latitude": -33.87, "longitude": 151.2, "radius_m": 150 }
```

Radius must be 50–300 m, enforced by a `CHECK` constraint as well as by validation. Delete is a
soft delete — shifts keep pointing at the zone they were started in.

## Shifts

| Endpoint | Role | Notes |
|---|---|---|
| `GET /api/shifts/current` | any | The open shift, or null. |
| `POST /api/shifts/start` | any | `{ latitude, longitude, accuracy_m }` → 201. All three required. |
| `POST /api/shifts/end` | any | Same fields, **all optional** — a denied location permission must never trap someone in an open shift. |
| `GET /api/shifts/mine` | any | `?period=week\|fortnight\|month`. Own shifts, with any edits attached. |
| `PATCH /api/shifts/{id}` | owner | Correct the times. |

Starting a shift needs a GPS fix accurate to **100 m or better** and a position inside a zone.
Ending is allowed anywhere, with the location recorded when given.

Editing takes wall-clock times in the business's timezone, so an owner in another state still
edits in shop hours. `reason` is required. Omitting a time leaves it as it is; setting `ended_at`
on an open shift closes it.

```json
{ "started_at": "2026-09-18T09:00:00", "ended_at": "2026-09-18T16:30:00",
  "reason": "Forgot to clock in at the start of the shift" }
```

Every edit is appended to `shift_edits` and returned on the shift from then on — for the employee
too, not just the owner.

## Live board and overview

| Endpoint | Role |
|---|---|
| `GET /api/shifts/live` | owner, manager |
| `GET /api/overview` | owner |

## Availability

| Endpoint | Role | Notes |
|---|---|---|
| `GET /api/availability/mine` | any | |
| `PUT /api/availability/mine` | any | Replaces the whole week: `{ "days": [{ "weekday": 0, "start_time": "09:00", "end_time": "17:00" }] }`. Monday is 0, at most 7 entries. |
| `GET /api/availability/team` | owner, manager | |

## Timesheets — owner only

| Endpoint | Notes |
|---|---|
| `GET /api/timesheets` | `?period=week\|fortnight\|month&user_id=<uuid>`. Default `fortnight`. Totals, per-employee hours, every shift with its edits, and the staff list for the filter. |
| `GET /api/timesheets/export.csv` | Same parameters, as a download. |

## Payroll — owner only

| Endpoint | Notes |
|---|---|
| `GET /api/payroll` | `?period=…`. One line per person per day. |
| `GET /api/payroll/export.csv` | `Payroll code,Employee,Date,Hours`. |

Hours are summed in full then rounded **once** at the end, half-up, to the nearest 15 minutes
(`PAYROLL_ROUNDING_MINUTES`, 0 for exact times).

`ready` is false when a shift in the period is still open — an unfinished shift has no duration to
pay. `missing_codes` lists people without a payroll code; that is a **warning, not a blocker**, so
a run can be `ready: true` with codes missing.

Both CSV exports quote any cell starting with `=`, `+`, `-` or `@`, so a staff member named by a
formula can't execute in the bookkeeper's spreadsheet.

## Business

| Endpoint | Role | Notes |
|---|---|---|
| `PATCH /api/business` | owner | `{ name?, abn?, timezone? }`. The ABN is checksum-validated, not just length-checked. |
| `GET /api/business/onboarding` | owner | Wizard steps, what is done, days left in the trial, seat usage. |

## Health

| Endpoint | Notes |
|---|---|
| `GET /health` | Liveness. No dependencies on purpose — it answers even when the database is down. |
| `GET /health/ready` | Readiness. 503 `database_unavailable` until Postgres is reachable. |

Both sit outside `/api`.

## Error codes

Every error has the same shape:

```json
{ "detail": { "code": "outside_zone",
              "message": "You're too far from Harbour St to start a shift.",
              "distance_m": 5560 } }
```

`code` is stable — branch on it. `message` is written to be shown to a person unchanged. Extra
keys carry whatever the UI needs to explain the refusal.

| Status | Code | Meaning |
|---|---|---|
| 400 | `nothing_to_change` | The edit would change nothing. |
| 401 | `invalid_credentials` | Wrong email or password. |
| 401 | `not_authenticated` | No token. |
| 401 | `invalid_token` / `token_expired` | Bad or expired token — refresh. |
| 401 | `session_revoked` | `token_version` moved on. Sign in again. |
| 403 | `forbidden` | Wrong role for this endpoint. |
| 403 | `account_inactive` | The user is archived or never joined. |
| 402 | `billing_inactive` | Read-only or suspended: reads fine, writes refused. |
| 404 | `invalid_invite` / `reset_invalid` | Used, expired or invented token. |
| 404 | `location_not_found` / `member_not_found` / `shift_not_found` | |
| 409 | `shift_already_open` | One open shift per person. |
| 409 | `no_open_shift` | Nothing to end. |
| 409 | `outside_zone` | Too far away. Carries `distance_m`. |
| 409 | `gps_inaccurate` | Fix worse than 100 m. Carries `accuracy_m`. |
| 409 | `no_zone_configured` | The business has no active zones yet. |
| 409 | `seat_limit_reached` | Archive someone or raise the limit. |
| 409 | `email_taken` | Emails are globally unique. |
| 409 | `payroll_code_taken` | Unique per business. |
| 409 | `future_time` / `end_before_start` | Rejected shift edit. |
| 409 | `cannot_archive_owner` / `not_archived` / `not_invited` / `never_joined` | State the action doesn't apply to. |
| 422 | `invalid_request` | Validation failed. Carries `fields`. |
| 429 | `too_many_attempts` | Locked for 15 minutes. |
| 500 | `server_error` | Carries `request_id`, which matches the log line. Never a stack trace. |
| 503 | `database_unavailable` | Readiness only. |
