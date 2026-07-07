# FinnGuide — Week 1 Build Log

A detailed record of everything built in the Week 1 foundation phase: what was
done, how, why, and the problems hit along the way. This is the developer
narrative behind commit `4d7a2dc`.

- **Date:** July 2026
- **Milestone:** Week 1 — Foundation (per PRD §9)
- **Repo:** https://github.com/Awais-niazi/wayfara
- **Outcome:** Django backend with auth + onboarding profile, Expo app with
  NativeWind styling, landing placeholder, all committed and pushed.

---

## 1. Decisions made this session (and why)

Three decisions changed the plan from what the PRD v1.0 describes. Each is also
saved to persistent project memory so future sessions honour it.

### 1.1 React Native, not a React PWA

The PRD specifies a Progressive Web App. We changed this to a **React Native
mobile app** (via Expo) — the product is meant to be a real installable mobile
app, not a web app.

Knock-on effects: NativeWind replaces web Tailwind; app-store distribution
replaces "no app store needed"; and store payment rules become relevant (see
next).

### 1.2 Payments happen on the web, through a Pakistani gateway

Two sub-decisions:

- **Not in-app purchase.** Apple/Google take 15–30% on digital unlocks bought
  inside a native app. Instead, users buy on the **FinnGuide website** and the
  app unlocks by signing in to an account that owns the entitlement
  (the Netflix/Spotify model). To satisfy Apple/Google anti-steering rules, the
  in-app UI stays neutral — locked content says "sign in with a Full Access
  account", it does not link out to a purchase page.
- **Not Stripe.** Stripe does not operate in Pakistan, and the buyers are in
  Pakistan paying with local methods. The checkout will use a Pakistani gateway
  (likely **Safepay** or **PayFast** — both SBP-licensed, ~2–3.5% fee) covering
  **Easypaisa, JazzCash, and local bank cards**. Pricing shown in PKR.

On the backend this is unchanged in shape: the gateway's webhook flips
`User.tier`, exactly as a Stripe webhook would have.

> Merchant onboarding for Pakistani gateways needs a Pakistani business
> registration/NTN + local bank account — worth sorting before the late-August
> move to Finland.

### 1.3 A dedicated PostgreSQL cluster (port 5433)

The machine already runs PostgreSQL on the default port 5432 — but that cluster
is an **intentional read-only replica of "Ash"** (Awais's personal AI), whose
primary database lives on a server in Helsinki. It shows
`pg_is_in_recovery() = t` by design.

**That cluster must never be modified or promoted** (promoting would detach the
replica from Helsinki and break the backup). FinnGuide therefore got its own
isolated cluster, `16/finnguide`, on **port 5433**.

---

## 2. Backend (`backend/`)

**Stack:** Django 6.0.7 · Django REST Framework 3.17.1 ·
djangorestframework-simplejwt 5.5.1 · psycopg 3.3.4 · dj-database-url 3.1.2 ·
django-cors-headers 4.9.0 · python-dotenv · PostgreSQL 16.

### 2.1 How it was created

```bash
mkdir backend && cd backend
python3 -m venv .venv
.venv/bin/pip install Django djangorestframework djangorestframework-simplejwt \
  "psycopg[binary]" dj-database-url django-cors-headers python-dotenv
.venv/bin/django-admin startproject finnguide .
.venv/bin/python manage.py startapp accounts
```

Project = `finnguide`, first app = `accounts`.

### 2.2 Settings — environment-driven

[`finnguide/settings.py`](../backend/finnguide/settings.py) was rewritten so
nothing environment-specific is hardcoded:

- `python-dotenv` loads `backend/.env` if present.
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` all read from
  env with safe dev defaults.
- **Database:** `dj_database_url` reads `DATABASE_URL`. If it is unset, it
  **falls back to SQLite** — so a fresh clone runs with zero setup, while real
  dev and production use Postgres.
- DRF configured with JWT as the default authentication class and
  `IsAuthenticated` as the default permission.
- SimpleJWT: 60-min access tokens, 30-day refresh tokens, rotation on.
- `AUTH_USER_MODEL = "accounts.User"`.

### 2.3 The custom User model

[`accounts/models.py`](../backend/accounts/models.py) — one table doing three
jobs. Email is the login (no username), via a custom `UserManager`.

| Group | Fields |
|-------|--------|
| **Identity** | `email` (unique login), `password`, `first_name`, `last_name`, Django's `is_active/staff/superuser`, `date_joined`, `last_login` |
| **Onboarding profile** (PRD Phase 0) | `study_level`, `field_of_study`, `grades`, `language_test_status`, `language_test_score`, `budget_eur_per_year`, `intake`, `intake_year`, `stage` |
| **Journey & entitlement** | `current_phase` (0–6), `tier` (`free`/`full`/`premium`), `onboarding_completed` |

Choice fields use Django `TextChoices` enums (StudyLevel, LanguageTestStatus,
Intake, Stage, Tier).

**Design note:** `tier` is deliberately **read-only through the API** — only the
future payment webhook can change it, so a user can never upgrade themselves by
PATCHing their profile. This is enforced in the serializer and covered by a test.

### 2.4 API surface

Serializers ([`accounts/serializers.py`](../backend/accounts/serializers.py)):

- `RegisterSerializer` — email + password (+ optional names); password run
  through Django's validators; write-only.
- `ProfileSerializer` — exposes the full profile; `id`, `email`, `tier`,
  `current_phase` are read-only.

Views ([`accounts/views.py`](../backend/accounts/views.py)):

- `RegisterView` — `CreateAPIView`, `AllowAny`.
- `ProfileView` — `RetrieveUpdateAPIView`; `get_object()` returns
  `request.user`, so it always acts on the authenticated user.

Routes:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/auth/register/` | Create account |
| POST | `/api/auth/token/` | Log in → access + refresh JWT |
| POST | `/api/auth/token/refresh/` | Refresh access token |
| GET / PATCH | `/api/profile/` | Read / update onboarding profile |

Also: a custom `UserAdmin` ([`accounts/admin.py`](../backend/accounts/admin.py))
grouping the profile and entitlement fields for the Django admin.

### 2.5 Tests

[`accounts/tests.py`](../backend/accounts/tests.py) — 5 tests, all passing:

1. Register → login → fetch profile (happy path; asserts default `tier=free`).
2. Registration rejects a weak password.
3. Profile endpoint requires authentication (401 without a token).
4. Onboarding PATCH persists profile fields.
5. `tier` cannot be changed via the API (stays `free` after trying to PATCH it).

### 2.6 Supporting files

- `requirements.txt` — frozen dependency list.
- `.env.example` — template documenting `DATABASE_URL` etc.

---

## 3. Database & the Postgres cluster

### 3.1 The detour that mattered

The first `createdb` attempt failed (`role "awais-faiz" does not exist`), and
creating the role surfaced that the default cluster was **read-only / in
recovery**. Investigation (`SELECT pg_is_in_recovery()` → `t`) plus Awais's
context revealed it is Ash's deliberate Helsinki replica — not a fault, and not
to be touched. Hence the separate cluster.

### 3.2 Commands used

Run by Awais (needed `sudo`):

```bash
sudo pg_createcluster 16 finnguide --port 5433 --start
sudo -u postgres psql -p 5433 -c 'CREATE ROLE "awais-faiz" LOGIN CREATEDB;'
```

Then, from the assistant:

```bash
createdb -p 5433 finnguide
# backend/.env:
#   DATABASE_URL=postgres://awais-faiz@:5433/finnguide
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test      # 5 passed on Postgres
rm db.sqlite3                        # drop the earlier SQLite fallback file
```

### 3.3 Resulting schema

Domain table `accounts_user` (all fields from §2.3) plus Django's standard
infrastructure tables: `auth_group`, `auth_permission`,
`accounts_user_groups`, `accounts_user_user_permissions`, `django_admin_log`,
`django_content_type`, `django_migrations`, `django_session`.

`accounts_user` has a unique index on `email` and CHECK constraints on the
unsigned integer fields (`budget_eur_per_year`, `intake_year`, `current_phase`).

### 3.4 Still to come (PRD §8.3)

`UserTimeline`, `Phase`, `Step`, `UserStep`, `ChecklistItem`, `Notification`,
`University`, `ChatSession`, `DocumentUpload`, plus a `Payment` table (added to
the plan so every gateway transaction/webhook is auditable, not just the
resulting tier flag). Phase/step content lives in the DB so it is editable from
admin without a redeploy — this is what makes the PRD's "update content when
Migri changes rules" mitigation work.

---

## 4. Mobile app (`mobile/`)

**Stack:** Expo SDK ~57.0.4 · React Native 0.86 · React 19.2 · TypeScript ·
NativeWind v5 (Tailwind CSS v4).

### 4.1 Scaffold

```bash
npx create-expo-app@latest mobile --template blank-typescript
```

### 4.2 The NativeWind problem (and the fix)

This was the main engineering hurdle of Week 1.

- First attempt used **NativeWind v4** (the stable release) with Tailwind 3.4.
  Typecheck passed, but bundling the app failed with
  `TypeError: Cannot read properties of undefined (reading 'transformFile')`.
- Web results pointed at an unrelated old Node-17 issue. Reading the actual
  source in `node_modules/react-native-css-interop/dist/metro/` showed the real
  cause: NativeWind v4's Metro integration monkey-patches internal bundler
  methods that **changed in Metro 0.84** (the version Expo SDK 57 ships). v4 is
  simply not compatible with SDK 57.
- **Fix:** migrated to **NativeWind v5 preview**, which has a different
  architecture (Tailwind v4 + `react-native-css`, no Babel plugin, styles
  compiled into the JS bundle). Followed NativeWind's official v5 install docs.

```bash
npm remove nativewind tailwindcss prettier-plugin-tailwindcss
npm pkg set overrides.lightningcss="1.30.1"
npx expo install nativewind@preview react-native-css
npm install --save-dev tailwindcss @tailwindcss/postcss postcss
```

### 4.3 Configuration files

- [`metro.config.js`](../mobile/metro.config.js) — wraps Expo's config with
  `withNativewind`.
- [`global.css`](../mobile/global.css) — Tailwind v4 `@import`s plus a `@theme`
  block defining the FinnGuide brand colors (`--color-primary: #002f6c`,
  `--color-accent: #0053a5`).
- `postcss.config.mjs` — `@tailwindcss/postcss` plugin.
- `nativewind-env.d.ts` / `declarations.d.ts` — TypeScript types for className
  props and CSS side-effect imports.
- Removed v4's `babel.config.js` and `tailwind.config.js` (not used in v5).

### 4.4 App code

- [`App.tsx`](../mobile/App.tsx) — welcome screen using NativeWind classes
  (`text-primary`, etc.) inside a `SafeAreaProvider`.
- [`lib/api.ts`](../mobile/lib/api.ts) — a small typed API client
  (`register`, `login`, `getProfile`) that reads its base URL from
  `expo-constants`, ready to talk to the Django endpoints.

### 4.5 Verification

- `expo-doctor` → **20/20 checks passed** (after adding the
  `react-native-worklets` peer dep that Reanimated needs).
- `tsc --noEmit` → clean.
- `expo export --platform android` → **bundles successfully** (the v4 crash is
  gone).
- Sanity-checked the compiled Hermes bytecode: the brand color `002f6c` is
  present in the bundle, confirming NativeWind v5 actually processes the
  `@theme` color and utility classes end to end — not just that it compiles.

> **Caveat:** NativeWind v5 is preview software. It works today; if it causes
> friction later, the fallback is pinning a known-good nightly or waiting for
> stable.

---

## 5. Web landing placeholder (`web/`)

[`web/index.html`](../web/index.html) — a static placeholder for the landing +
purchase front door. Shows the tagline, PKR pricing (Full Access Rs 7,500 /
Premium Rs 12,500), the "pay with Easypaisa/JazzCash/card then sign in to
unlock" messaging, and the "guidance tool, not a legal service" disclaimer.
Actual checkout wiring is scheduled for Week 9.

---

## 6. Repo hygiene & git

- `git init -b main`.
- [`.gitignore`](../.gitignore) covers `.claude/`, the venv, `backend/.env`,
  `node_modules`, `.expo`, `__pycache__`, SQLite files, logs.
- **Migrations:** initially git-ignored, then **un-ignored** — for a
  production-ready app, migration files are the versioned schema history and
  must be committed so every environment (and the eventual Railway/Render
  deploy) builds an identical schema.
- [`README.md`](../README.md) documents the monorepo layout, key decisions, and
  local setup for both backend and mobile.
- First commit **`4d7a2dc`** — 43 files, verified to contain no build
  artifacts or secrets.
- Remote `origin` → `https://github.com/Awais-niazi/wayfara.git`, pushed to
  `main` (SSH key added to GitHub by Awais).

---

## 7. Where things stand

**Done (Week 1 foundation):** email-based auth + JWT, onboarding profile model,
isolated Postgres, styled Expo app with a working API client, landing
placeholder, everything committed and pushed.

**Next (Week 2 — Onboarding, PRD §9):** the timeline-generation engine
(`Phase`/`Step`/`UserTimeline`/`Notification` models + the backwards-deadline
algorithm), then the app-side onboarding flow and the motivating result screen.
Recommended order: backend timeline engine first, since the onboarding UI needs
those endpoints to render a real timeline.

## Appendix — open items to revisit

1. **Migrations vs deploy target** — committed now; reconcile when the backend
   is first deployed.
2. **NativeWind v5 preview** — monitor for a stable release.
3. **Pakistani gateway merchant onboarding** — needs Pakistani business docs;
   do before the late-August move.
4. **Migri financial figures** (€560/mo, €6,720/yr in the PRD) — verify against
   Migri's current numbers before writing Phase 4 content, and keep them
   CMS-editable.
