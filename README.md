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

## Backend — local setup

Wayfara uses its **own PostgreSQL cluster on port 5433** (cluster `16/finnguide`,
database `wayfara`), kept separate from anything else on the machine.

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # DATABASE_URL points at postgres on :5433
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test
.venv/bin/python manage.py runserver
```

Without a `DATABASE_URL`, the backend falls back to SQLite so a fresh clone runs
with zero setup.

### API endpoints

- `POST /api/auth/register/` — create account (email + password)
- `POST /api/auth/token/` + `/api/auth/token/refresh/` — JWT login
- `GET|PATCH /api/profile/` — read/update onboarding profile

## Mobile — local setup

```bash
cd mobile
npm install
npx expo start
```

## Status

Week 1 scaffold: Django backend with email-based auth + onboarding profile,
Expo app with NativeWind styling, landing placeholder.
