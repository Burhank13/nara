# Nara

Shift logging for small businesses that pay people by the hour — car washes, cafés, cleaners.
Staff clock in from their phone, and the app checks they are actually at the shop before it
starts the clock. The owner sees who is on shift right now, fixes the inevitable "I forgot to
clock in", and exports the week's hours for payroll.

Built for Australian small businesses: ABN validation, `Australia/Sydney` as the default
timezone, and hours that a bookkeeper can reconcile.

```
Employee's phone                  Owner's laptop
  clock in / out                    who's on now
  own hours                         timesheets + edits
  availability                      payroll CSV
        \                          /
         \                        /
          React SPA  →  /api  →  FastAPI  →  Postgres
```

## Quick start

You need Docker, Python 3.13 and Node 22.

```bash
git clone https://github.com/Burhank13/nara.git
cd nara
cp .env.example backend/.env
docker compose up -d                        # Postgres on :5432
```

Backend, in its own terminal:

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m alembic upgrade head
python -m app.seed                                # demo business + accounts
python -m uvicorn app.main:app --reload
```

Frontend, in another:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in as `owner@carwash.demo` / `narademo123`.
The seed also creates `manager@carwash.demo` and `employee@carwash.demo` on the same password,
plus one unaccepted invite so you can see that flow.

**The seed creates no shop zone.** Nobody can clock in until one exists — sign in as the owner,
open **Locations**, and drop a zone on wherever you are. Clocking in also needs a GPS fix
accurate to 100 m or better, which a laptop on Wi-Fi usually fails; use a phone, and see
[docs/operations.md](docs/operations.md#demoing-on-a-real-phone) for how to reach the dev server
over HTTPS.

## What's in the box

| Area | What it does |
|---|---|
| **Geofenced clock-in** | Haversine distance to the nearest zone that contains you; 50–300 m radius. Start refused outside the zone or on a vague fix; end allowed anywhere, with the location recorded. |
| **Live board** | Who is on shift now, how long they have been, and which site. |
| **Timesheets** | Week/fortnight/month in the business's own timezone, per person and total, CSV export. |
| **Shift edits** | The owner can correct times. A reason is required, and every edit is kept in an append-only audit log the employee can see. |
| **Payroll export** | One line per person per day, hours rounded half-up to the quarter hour, CSV. |
| **Availability** | A weekly grid each person fills in; owners and managers see the team's. |
| **Team and seats** | Email invites that expire in 7 days, seat limits enforced under a row lock, archive and restore. |
| **Accounts** | 14-day trial → read-only; past due keeps working for a 7-day grace period → suspended. |

Three roles. **Owner** runs the business. **Employee** clocks in, sets availability, sees their
own hours. **Manager** is "employee plus": everything an employee can do, plus a read-only live
board and availability grid — no shift editing, no exports, no billing.

## Repository layout

```
backend/
  app/
    models/      SQLAlchemy tables
    schemas/     Pydantic request/response shapes
    routes/      HTTP endpoints, thin — they validate and delegate
    services/    the business rules live here
    config.py    every setting, with its default and why
    main.py      app assembly; all routers mounted under /api
  alembic/       migrations, 0001 upward
  tests/         the backend suite, against a real Postgres
frontend/
  src/
    screens/     one file per route
    components/  shared UI
    lib/         API client, geolocation, formatting
  e2e/           Playwright specs, run at desktop and phone viewports
docs/            architecture, API reference, runbook
Dockerfile       one image: API + built frontend on a single origin
```

## Tests

```bash
cd backend  && python -m pytest          # needs Postgres up
cd backend  && python -m ruff check . && python -m ruff format --check .
cd frontend && npm run build             # tsc -b runs first
cd frontend && npm run lint
cd frontend && npm run e2e               # needs API + Vite running
```

The backend suite creates and migrates its own `nara_test` database, so it never touches your
development data. It also blanks `RESEND_API_KEY`, so no test ever emails anyone.

All of this runs on every push and pull request — see [.github/workflows/ci.yml](.github/workflows/ci.yml).
The browser tests are a separate job, so a slow or flaky one doesn't hold up the fast feedback.

Playwright drives the Chrome already installed on the machine rather than downloading a browser
bundle. If you don't have Chrome, change `CHANNEL` in `frontend/playwright.config.ts` to `msedge`.

## Configuration

Everything is environment variables, read once at startup from `backend/.env`.
[`.env.example`](.env.example) lists every one with a comment explaining it; the defaults in
[`backend/app/config.py`](backend/app/config.py) are what runs if you set nothing.

The ones that actually matter:

| Variable | Why you'd change it |
|---|---|
| `DATABASE_URL` | Where Postgres is. |
| `JWT_SECRET` | Must be 32+ characters outside development — the app refuses to boot otherwise. |
| `APP_BASE_URL` | The public URL invite and password-reset links are built from. Get this wrong and every link you send is dead. |
| `RESEND_API_KEY` | Blank means invite and reset links are logged to the console instead of emailed, which is what you want locally. |
| `MAX_GPS_ACCURACY_M` | 100 m. Loosening it lets laptop Wi-Fi fixes start shifts. |
| `PAYROLL_ROUNDING_MINUTES` | 15. Set to 0 to export exact times. |
| `SENTRY_DSN` | Blank turns error alerting off. Set it and crashes are reported, tagged with the request id the caller saw. |

## Deploying

The `Dockerfile` builds one image: the API also serves the built frontend, so the browser talks
to a single origin, the refresh cookie stays `SameSite=lax`, and CORS is out of the request path
entirely. Migrations run before the first request, so a deploy can never serve an old schema.

```bash
docker compose --profile prod up --build     # http://localhost:8080
```

See [docs/operations.md](docs/operations.md) for deploying somewhere real.

## Where to read next

- **[docs/architecture.md](docs/architecture.md)** — how it fits together and why it's built this way.
- **[docs/api.md](docs/api.md)** — endpoint reference, auth, error codes.
- **[docs/operations.md](docs/operations.md)** — running it, demoing it, fixing it when it breaks.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — conventions and how to add a migration.

## Status

Working and tested end to end, not yet deployed anywhere. Known gaps: no Stripe integration
(the account states exist, nothing charges a card), the payroll CSV is a generic
`Payroll code,Employee,Date,Hours` rather than a Xero or MYOB import template, zones are set by
coordinates with no map picker, and there are no trial nudge emails or admin console.
