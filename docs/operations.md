# Operations

Running Nara: locally, in front of a customer, and in production.

## Running it locally

Three things have to be up, in this order.

```bash
# 1. Postgres
docker compose up -d
docker compose ps                      # wait for "healthy"

# 2. API — from backend/
python -m alembic upgrade head
python -m uvicorn app.main:app --reload

# 3. Frontend — from frontend/
npm run dev
```

The API reads `backend/.env` **once at startup**. With `--reload` a change to a source file
restarts it, but a change to `.env` alone does not — stop and start it.

### Seeding

```bash
cd backend && python -m app.seed
```

Creates "Sparkle Car Wash" with `owner@`, `manager@` and `employee@carwash.demo`, all on
`narademo123`, plus one unaccepted invite for `newstarter@carwash.demo`.

Re-running it **resets those passwords** rather than skipping. That is deliberate: skipping let
`DEMO_PASSWORD` in the source drift from the hashes in the database, and sign-in then failed with
credentials that looked correct in the code.

The seed creates **no shop zone**, so nobody can clock in until you add one.

### Reaching it from a phone on your LAN

You can't, usefully. Browsers only hand out geolocation on a secure origin, so plain HTTP to your
laptop's LAN address will load the app but never let anyone clock in. Use a tunnel.

## Demoing on a real phone

The clock-in has to happen on a phone — a laptop locates itself by Wi-Fi, typically to ±500 m,
which the 100 m accuracy gate refuses by design. And the phone needs HTTPS. A quick tunnel gives
you both without a domain or a host.

**Order matters:** get the tunnel URL *before* starting the API, or you will have to restart it.

```bash
# 1. Postgres
docker compose up -d

# 2. Frontend
cd frontend && npm run dev

# 3. Tunnel — prints https://<words>.trycloudflare.com
cloudflared tunnel --url http://localhost:5173
```

No install needed; the standalone binary works on its own:

```bash
curl -L -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
```

**4.** Put that URL in `backend/.env`:

```
APP_BASE_URL=https://<words>.trycloudflare.com
CORS_ORIGINS=http://localhost:5173,https://<words>.trycloudflare.com
```

`APP_BASE_URL` is what invite and reset links are built from. Leave it on `localhost` and every
link you hand a customer is dead.

**5.** Start the API last, so it reads the URL you just set.

Vite rejects requests under a hostname it doesn't know. `frontend/vite.config.ts` allows
`.trycloudflare.com`, `.ngrok-free.app`, `.ngrok.app` and `.loca.lt`; anything else needs adding
to `allowedHosts` first.

### Before you present

- Create a zone **standing where the demo will happen**. The geofence is real.
- Sign up a fresh business in front of them rather than using the seed — the onboarding wizard is
  the convincing part, and the business ends up in their name.
- Use the **Copy link** button for invites. Until a domain is verified at resend.com/domains,
  Resend only delivers to the account owner's own address; an invite to anyone else silently
  doesn't arrive.
- Don't go near billing — the account states are real, but nothing charges a card.

Killing the tunnel changes the URL and kills every invite link already sent.

## Deploying

The `Dockerfile` builds one image: Node builds the frontend, then the Python stage serves the API
*and* those built files, so there is one origin and one URL to configure.

```bash
docker compose --profile prod up --build     # http://localhost:8080
```

Migrations run in the container's `CMD` before uvicorn starts, so a deploy can never serve an
older schema than its code.

### What must be set in production

| Variable | |
|---|---|
| `ENVIRONMENT` | Anything but `development`. This turns on HSTS and `Secure` cookies. |
| `JWT_SECRET` | 32+ characters. **The app refuses to start otherwise.** `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | Managed Postgres 16. |
| `APP_BASE_URL` | Your real public URL. |
| `CORS_ORIGINS` | The same URL. Single-origin means this is mostly moot, but keep it right. |
| `RESEND_API_KEY`, `EMAIL_FROM` | From a **verified domain**, or delivery is limited to your own address. |
| `SENTRY_DSN` | Optional but recommended. Blank turns error alerting off entirely. |

Changing `JWT_SECRET` signs everyone out. That is the emergency "revoke every session" lever.

### Error alerting

Set `SENTRY_DSN` and crashes are reported. Each event is tagged `request_id` with the same id
returned in the 500 body, so a customer quoting "request ab12cd34" leads straight to the event
rather than a search through everything that broke that minute.

Anything logged at ERROR becomes an event too, which is how a failed email send reaches you —
`send()` never raises, so the log line is the only signal.

`send_default_pii` is off: staff names, emails and clock-in coordinates are the whole database
here, and an alert needs the stack trace, not the person it happened to. Performance tracing is
off as well (`SENTRY_TRACES_SAMPLE_RATE=0.0`) — it bills per transaction, and errors are the
point. Raise it if you get a slow endpoint worth measuring.

To check it is live, cause a crash on a staging deploy and confirm the event arrives with the
tag. Do not test it in production.

### Health checks

- `GET /health` — liveness. Deliberately has no dependencies, so it answers while the database is
  down and your orchestrator doesn't restart-loop a healthy process over a database blip.
- `GET /health/ready` — readiness. 503 until Postgres answers. Point your load balancer here.

### Rate limiting

The app locks an account after 8 failed sign-ins. That is per-account, not per-IP — **per-IP
limits belong at your proxy or CDN**, not in the app process. Put something in front of this
before it's public.

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every push to `main` and every
pull request:

| Job | What it does |
|---|---|
| **Backend** | ruff lint and format, `alembic upgrade head`, `alembic check` for model drift, a full down-and-up migration cycle, then the test suite against a real Postgres service container. |
| **Frontend** | oxlint, and `npm run build` — which is `tsc -b && vite build`, so it typechecks too. |
| **Browser tests** | Starts Postgres, the API and the dev server, installs Chrome, runs Playwright. Depends on the other two, so it only runs once they pass. Traces from a failure are uploaded as an artifact. |

The browser job is deliberately separate and last: it is the slow one, and a flake in it should
not hide a lint error. It retries once on CI only — locally a flake is worth seeing.

`alembic downgrade base` is exercised on every run because the test suite depends on it, and a
downgrade nobody has tried is a downgrade that does not work.

## Migrations

```bash
cd backend
python -m alembic revision --autogenerate -m "add thing"   # review it, always
python -m alembic upgrade head
python -m alembic downgrade -1
python -m alembic check                                    # model/migration drift
```

Autogenerate misses enum value changes, index predicates and check constraints. Read the
generated file before committing it.

## Backups

`docker compose` keeps Postgres on a named volume, `postgres_data`.

```bash
docker compose exec postgres pg_dump -U nara nara > backup.sql
docker compose exec -T postgres psql -U nara nara < backup.sql
```

`docker compose down -v` destroys that volume. There is no other copy.

## Troubleshooting

**Sign-in fails with credentials that look right.** Re-run `python -m app.seed`; it resyncs the
demo passwords. If it's a real account, it may be locked — 8 failures locks it for 15 minutes,
and the response is 429 `too_many_attempts`, not a 401.

**Invite links point at localhost.** `APP_BASE_URL` is stale, or the API wasn't restarted after
you changed it. It is read once at startup.

**Clocking in says "use your phone for a reliable location check".** Working as intended — that's
`gps_inaccurate`, a fix worse than 100 m. Use a phone, or raise `MAX_GPS_ACCURACY_M` if you're
only testing.

**Clocking in says there's no shop zone.** There isn't one. Owner → Locations.

**Vite says "Blocked request. This host is not allowed."** Add the hostname to `allowedHosts` in
`frontend/vite.config.ts`.

**A deep link returns JSON instead of the app.** Something is mounted outside `/api`. Every router
belongs under the prefix in `main.py`.

**The test suite wiped my development data.** It shouldn't — it targets `TEST_DATABASE_URL` and
runs `alembic downgrade base`. Check that `DATABASE_URL` and `TEST_DATABASE_URL` name *different*
databases before running it.

**Tests try to send real email.** `conftest.py` blanks `RESEND_API_KEY`. Don't remove that.

**Playwright can't download a browser.** It's configured to drive installed Chrome
(`channel: 'chrome'`). Switch `CHANNEL` in `playwright.config.ts` to `msedge` if you don't have it.

**A 500 in the logs.** Find the `request_id` in the response and grep the logs for it. Responses
never carry stack traces.
