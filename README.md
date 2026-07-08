# Wayfara

The complete, step-by-step guide for Pakistani students moving to Finland —
from choosing a university to their first month settled in. Replaces the
€1,500 education consultant with a €25 app.

> _"Why pay a consultant €1,500? Do it yourself for €25."_

## Monorepo layout

| Path | What it is | Stack |
|------|-----------|-------|
| `backend/` | REST API, business logic, AI orchestration | Django 6 + DRF + SimpleJWT + PostgreSQL |
| `mobile/` | The app users install | Expo (React Native, SDK 57) + NativeWind v5 (Tailwind) |
| `web/` | Landing page + purchase front door | Static HTML (checkout wiring lands Week 9) |

## Key decisions

- **Mobile app, not a PWA** — React Native via Expo.
- **Payments happen on the web, not in-app.** Users buy on the website through a
  Pakistani gateway (Easypaisa / JazzCash / cards; Stripe does not operate in
  Pakistan), then unlock the app by signing in — avoids Apple/Google's 15–30% cut.
- **Tiers:** Free (Phases 0–1) · Full Access · Premium (adds AI document review).
  `User.tier` is read-only via the API; only the payment webhook changes it.
- **Onboarding is form-first.** No register wall: the Get Started form creates a
  passwordless account, university matching + timeline generation run in the
  background, and a 6-digit OTP email verifies the user (OTP is also the login).
- **Background tasks: Celery + Redis.** Tasks are thin invokers only — business
  logic lives in service functions. Local Redis db index 5 (shared Redis server).

## Backend — local setup

Wayfara uses its **own PostgreSQL cluster on port 5433** (cluster `16/finnguide`,
database `wayfara`), kept separate from anything else on the machine.

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # DATABASE_URL points at postgres on :5433
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_task_templates
.venv/bin/python manage.py test
.venv/bin/python manage.py runserver
```

Without a `DATABASE_URL`, the backend falls back to SQLite so a fresh clone runs
with zero setup. Celery tasks run inline by default (`CELERY_TASK_ALWAYS_EAGER=true`);
to exercise the real queue locally:

```bash
CELERY_TASK_ALWAYS_EAGER=false .venv/bin/celery -A wayfara worker --loglevel=info
# and run the server with CELERY_TASK_ALWAYS_EAGER=false too
```

### API endpoints

- `POST /api/onboarding/` — the Get Started form (anonymous): profile + email →
  account, background matching + timeline, OTP email
- `POST /api/auth/otp/request/` / `POST /api/auth/otp/verify/` — passwordless
  login; verify returns JWT tokens
- `POST /api/auth/token/refresh/` — refresh the access token
- `GET|PATCH /api/profile/` — read/update onboarding profile
- `GET /api/matches/` — university recommendations, best fit first
- `GET /api/tasks/` (`?phase=N`) + `POST /api/tasks/<id>/status/` — journey plan

### Data freshness (nightly scraper)

University/visa data is refreshed by a nightly scraper (2 AM Europe/Helsinki via
Celery Beat). Detected changes follow a **tiered policy**: low-risk fields
auto-apply; critical fields (deadlines, tuition, Migri figures) wait in a
review queue in Django admin (Scraping › Data changes) with an email alert.

```bash
.venv/bin/python manage.py setup_scraper_schedule   # register the 2 AM job (once)
# production also runs:
CELERY_TASK_ALWAYS_EAGER=false celery -A wayfara beat \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Per-site scraper classes (`scraping/scrapers.py`) are stubs — real parsing
selectors must be written and verified against the live sites before enabling a
source. Add a source: create a `ScrapeSource` whose `scraper_key` matches a
registered scraper.

## Mobile — local setup

```bash
cd mobile
npm install
npx expo start
```

## Status

Week 1 scaffold: Django backend with email-based auth + onboarding profile,
Expo app with NativeWind styling, landing placeholder.
