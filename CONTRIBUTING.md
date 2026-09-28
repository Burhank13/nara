# Contributing

Setup is in the [README](README.md). This is about how the code is written.

## Before you push

```bash
cd backend  && python -m ruff check . && python -m ruff format --check . && python -m pytest
cd backend  && python -m alembic check
cd frontend && npm run lint && npm run build && npm run e2e
```

CI runs all of this on every push and pull request. Running it locally first is still the
quicker way to find out.

## Where code goes

**Rules live in `app/services/`.** Routes validate input, call a service and shape a response —
if a route is making a decision, that decision is in the wrong file. Services take a `Session` and
plain arguments, not a `Request`, which is what makes them straightforward to test.

Models are the schema. Schemas (`app/schemas/`) are the wire format. They are allowed to differ,
and usually should — `BusinessResponse.of()` exposes a *derived* status, not the raw column.

## Comments

Comment the **why**, never the what. A comment earns its place by recording a decision, a
constraint or a trap someone would otherwise re-introduce:

```python
# Committed here rather than by the request: the caller raises 401 next, and a rolled-back
# count would let an attacker guess for ever.
db.commit()
```

```python
def round_hours(hours: float, increment_minutes: int) -> float:
    """Half-up, not banker's rounding: these are wages, and 7.125 h has to land on 7.25."""
```

`# increment the counter` above `count += 1` is noise. If you had to think about it, say what you
worked out; if it's obvious, say nothing.

## Errors

Always `api_error(status, code, message, **extra)`. The `code` is a stable contract the frontend
branches on — don't rename one without following it through the UI. The `message` is shown to a
person unchanged, so write it as something a car wash owner would want to read. `extra` carries
whatever the UI needs to explain the refusal:

```python
raise api_error(409, "outside_zone",
                f"You're too far from {zone.name} to start a shift.",
                distance_m=round(distance))
```

Add new codes to the table in [docs/api.md](docs/api.md#error-codes).

## Tests

Backend tests run against a real Postgres, not SQLite — the partial unique indexes, native enums
and `timestamptz` behaviour being tested don't exist in SQLite.

Name the behaviour, not the function:

```python
def test_a_reset_clears_a_lockout(...)
def test_an_unknown_address_is_answered_the_same_way(...)
def test_clock_in_is_refused_outside_the_zone(...)
```

Use the helpers in `tests/helpers.py` (`signup`, `invite`, `accept`, `join`, `create_zone`) rather
than rebuilding a business in each test.

Two traps worth knowing:

- Postgres `now()` is **constant within a transaction**, so rows created in one test share a
  `created_at`. Address a record by the id the API returned, not by "the most recent one".
- Never assert on wall-clock times without pinning the timezone. Period boundaries are computed in
  the business's timezone.

## Migrations

```bash
python -m alembic revision --autogenerate -m "add thing"
```

Read what it generated. Autogenerate does not see enum value changes, index predicates or check
constraints, and those are exactly what this schema relies on. Write the `downgrade` properly —
`alembic downgrade base` runs on every test session.

Prefer a database constraint to an application check whenever a race is possible. The existing
ones are listed in [docs/architecture.md](docs/architecture.md#the-database-enforces-what-matters).

## Frontend

- Screens in `src/screens/`, one per route. Shared pieces in `src/components/`.
- Server state is TanStack Query. Don't add a state library for it.
- Never call `fetch` directly — go through `lib/api.ts`, which adds the `/api` prefix, attaches
  the token, and handles refresh-and-retry.
- Mobile first. The e2e suite runs everything at 390 px and fails on sideways scroll. When it
  does, the cause is usually a grid or flex item defaulting to `min-width: auto` — add `min-w-0`.
- New route? Add it to the `NAV` table in `App.tsx` for the roles that should see it, and wrap it
  in `OwnerOnly` if it's owner-only. Route guards are not access control — the API check is.

## Secrets

Real keys go in `backend/.env`, which is gitignored. `.env.example` is committed and must only
ever hold placeholders. `conftest.py` blanks `RESEND_API_KEY` so the suite can't email anyone —
leave that alone.

## Commits

Say what changed and why, in the imperative:

```
Add password reset, and email invites instead of pasting links
Allow tunnel hostnames through the dev server
Add browser tests, and fix the sideways scroll they found on phones
```

Keep each commit self-consistent: green tests, lint clean.
