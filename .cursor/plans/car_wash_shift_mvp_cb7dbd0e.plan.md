# MAF shift logging: plan summary (updated 17 Sep 2026)

The full design canvas is the artifact "MAF Shift Log Plan". It has plan boards 1–6 and 11 screen mockups.

## Scope
- **Owner:** see employees, the weekly availability grid, who is on shift now, hours per employee for any period and team totals (with CSV export). The owner can also edit a shift's start or end time. A reason is required and each edit goes to the shift_edits audit log. Only the owner manages billing, seats and business settings.
- **Manager:** an Employee-plus role. Has every Employee permission below (clock in/out, set availability, view own hours) plus read-only visibility into the team: the live "who's on shift now" view and the weekly availability grid. A manager cannot edit shift times, cannot export, and has no billing/seat access.
- **Employee:** joins through an invite link. They can start a shift only inside a geofence (150 m default, GPS accuracy of 100 m or better) and can end it from anywhere, with location recorded. They set their availability and can see their own hours, including manager/owner edits.
- **Screens:** all roles can use either a phone or a desktop. It is one responsive React app, built mobile-first with Tailwind breakpoints (under 640 / 640–1023 / 1024 px and up).
  - **Owner on a phone:** bottom tabs, 2×2 KPI tiles, cards instead of tables, and bottom sheets.
  - **Owner on a desktop:** sidebar and side panels.
  - **Laptop clock-in:** laptops use Wi-Fi location, so a start with accuracy worse than 100 m is refused with "use your phone".
  - **Manager:** gets the team's read-only live board/availability view plus their own "My shift" tab for personal clock-in/hours (same as Employee).

## Onboarding
The owner goes through a self-serve wizard (target: about 15 min):
1. **Sign up:** creates a trialing business with 10 seats for 14 days.
2. **Business details:** name, ABN and time zone.
3. **Shop zones:** one or more sites, each with an address, map pin, a 50–300 m radius and a test link. A business can add more sites later. A shift start is checked against the nearest zone the employee is inside (no per-employee site assignment in the MVP); the matched site is recorded on the shift.
4. **Add staff:** by email or a share link. Invites expire in 7 days.
5. **Pick seats and pay:** Stripe Checkout, or skip and keep the trial.
6. **First-day checklist:** with nudge emails.

Employees join in 5 steps: open invite → name + password → allow location → add to home screen → set availability.

Account states:
- Trialing → Active (card added).
- Trialing → Read-only (day 14, no card).
- Active → Past due (payment fails) → Suspended after 7 days.
- Read-only or Suspended → Active when a card is added.
- Active → Cancelled (export available for 90 days).

In Read-only or Suspended, the owner can view and export. Staff can view their hours and end an open shift, but can't start a new one.

Trial emails go out on days 0, 2, 7, 11 and 14.

Assisted setup (A$149): you create the business in the admin console, and the owner gets a "claim account" email.

## Seat limits
A seat is one employee or manager who can clock in. The owner is free.
- **Uses a seat:** active users and invites that haven't expired.
- **Frees a seat:** archiving someone, or an invite expiring.

What's stored:
- `businesses.seat_limit` is copied from the Stripe subscription quantity by webhook (trial: 10).
- `seat_limit_override` is for your manual deals.
- `used` is counted live with SQL rather than stored.

Enforcement:
- `reserve_seat()` locks the business row (`SELECT … FOR UPDATE`), then counts seats.
- It returns 409 `seat_limit_reached` at the limit and 402 if the business is suspended or cancelled.
- It is called by invite, resend and restore.

Changing seats:
- Adding seats updates the Stripe quantity with proration. The webhook then sets `seat_limit`, and the API also re-fetches the subscription so the UI updates straight away.
- The API refuses to reduce seats below the number in use, and nobody is removed automatically.
- Turn off quantity changes in Stripe's customer portal.
- Store Stripe event IDs so repeated webhooks are skipped.

What owners see:
- A seat meter that turns amber at 80%.
- At 100%, the Invite button becomes "Add seats".

What you see:
- An admin console listing each business's seats, status, revenue and trial end.

## Stack
The existing maf repo stays: FastAPI, PostgreSQL 16 with SQLAlchemy 2 and Alembic, and React + Vite + TS as an installable PWA.
- Swap python-jose and passlib for PyJWT and bcrypt.
- Stripe Billing with seat quantity, Leaflet + OpenStreetMap with a geocoding API for the map step, Resend or Postmark for email, and Sentry for error alerts.
- Host on Render or Railway. Use Fly.io if you want a Sydney region.

## Build
The current `backend/app/models/user.py` (role: employee/manager, no owner; an unrelated pending/approved/rejected account_status) predates this plan and doesn't match it — Foundation replaces it rather than adapting it: owner/manager/employee roles, businesses, shop_zones, invites, shifts, availability and shift_edits tables, plus the trial/active/read-only/suspended/cancelled account states on the business.

About 220 h (about 11 weeks at 20 h/week), in 6 phases:
1. Foundation, 30 h
2. Clock in/out, 35 h
3. Live board, availability and responsive layouts, 45 h
4. Hours, edits and export, 35 h
5. Trial, seats and onboarding, 40 h
6. Harden, deploy and pilot, 35 h

Cost by approach:
- **Self-build:** under A$300 cash, plus your time (about A$13,200 at A$60/h).
- **Freelancer:** A$9k–19k.
- **AU agency:** A$24k–48k.

## Running cost (AUD/month, ex GST)
- **Launch (0–20 businesses):** A$22–47.
- **Growth (20–200 businesses):** A$162–352.

On top of that, Stripe charges 1.7% + A$0.30 per domestic card payment, plus 0.7% for Billing.

## Pricing
- **Price:** A$4 per seat per month, with an A$29 minimum that covers up to 7 seats, ex GST.
- **Free trial:** 14 days and up to 10 seats, with no card needed.
- **Annual plan:** 10 months' price for 12.
- **Optional setup:** A$149.
- **Founding offer:** 50% off for 12 months for the first 10 businesses.

Published competitor prices (AUD per user per month):

| Product | Price |
|---|---|
| Deputy Lite | A$6.75 (A$30 minimum) |
| Deputy Core | A$8.75 |
| Deputy Pro | A$13 |
| Tanda | A$12.80 |
| Connecteam | Free up to 10 users (USD pricing) |

Unit economics:
- **Margin:** about 92% on a business with 10 seats.
- **Launch break-even:** 3 customers cover launch hosting.
- **Payback:** about 26 customers kept for a year repay 220 h.