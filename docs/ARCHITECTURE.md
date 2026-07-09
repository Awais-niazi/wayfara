# Wayfara — Architecture

The single source of truth for **how Wayfara is built and why**. Structure,
decisions, and trade-offs across the whole system (backend, mobile, data,
infrastructure). Read this first when onboarding to the codebase or deciding
where a new feature belongs.

- **Companion docs:** [`database-schema.md`](database-schema.md) (field-level
  data model), [`week-1-build-log.md`](week-1-build-log.md) (the founding
  session narrative), and the top-level [`README.md`](../README.md) (quick
  setup).
- **Status as written:** July 2026. This is a living document — when an
  architectural decision changes, update the relevant section *and* its
  trade-off note rather than appending a new one.

---

## Table of contents

1. [Product context](#1-product-context)
2. [System overview](#2-system-overview)
3. [Foundational decisions](#3-foundational-decisions)
4. [Backend architecture](#4-backend-architecture)
5. [Mobile architecture](#5-mobile-architecture)
6. [Configuration & environments](#6-configuration--environments)
7. [The 13 production layers](#7-the-13-production-layers)
8. [Trade-offs & known debt](#8-trade-offs--known-debt)
9. [Roadmap & open items](#9-roadmap--open-items)

---

## 1. Product context

**What.** Wayfara is a mobile app that does the complete job of a study-abroad
agent for Pakistani students heading to Finland for a master's — from choosing a
university through admissions, the Migri residence permit, flights, and the
first month settled in.

**Why it exists.** Education consultants charge Pakistani families ~€1,500. The
whole journey is a knowable, repeatable process. Wayfara packages it into a
~€25 app: _"Why pay a consultant €1,500? Do it yourself for €25."_

**Business consequence that shapes the architecture.** The price gap means
**volume is the business model**. The system must (a) hold up under load from
launch, and (b) protect genuinely sensitive data — passports, transcripts, bank
statements, advisor voice notes. Both concerns are formalized as the
[13 production layers](#7-the-13-production-layers), which every feature is
checked against.

**Naming note.** The PRD v1.0 called the product _FinnGuide_; it was renamed
**Wayfara** in July 2026. Some historical identifiers keep the old name (the
Postgres cluster is `16/finnguide`); the database inside it is `wayfara`.

---

## 2. System overview

### Monorepo layout

| Path | What it is | Stack |
|---|---|---|
| `backend/` | REST API, business logic, AI orchestration, data pipeline | Django 6 · DRF · SimpleJWT · PostgreSQL 16 · Celery/Redis |
| `mobile/` | The installable app | Expo (React Native, SDK 57) · NativeWind v5 · React Navigation |
| `web/` | Landing page + purchase front door | Static HTML (checkout wiring lands later) |
| `docs/` | Architecture, schema, build logs | Markdown |

### Shape of the system

```
  ┌─────────────┐        HTTPS / JSON        ┌──────────────────────────┐
  │  Mobile app │ ───────────────────────▶  │  Django REST API          │
  │  (Expo RN)  │   JWT (OTP-issued)         │  (stateless, horizontally │
  │             │ ◀───────────────────────  │   scalable)               │
  └─────────────┘                            └───────────┬──────────────┘
        │                                                │
        │ buys entitlement on                            │ owns as source of truth
        ▼                                                ▼
  ┌─────────────┐   webhook flips      ┌──────────────────────────────────┐
  │ web + PK    │ ── User.tier ──────▶ │  PostgreSQL 16 (:5433, isolated) │
  │ gateway     │                      └──────────────────────────────────┘
  └─────────────┘                                        ▲
                                                         │ background work
                                          ┌──────────────┴───────────────┐
                                          │  Celery workers + Beat        │
                                          │  (Redis broker, db index 5)   │
                                          │  matching · timeline ·        │
                                          │  reminders · nightly scraper  │
                                          └───────────────────────────────┘
```

### Request lifecycle (the onboarding spine)

The canonical flow the whole system is built around — **form-first, no register
wall**:

1. **App → `POST /api/onboarding/`** (anonymous): profile + email. The backend
   creates a passwordless `User` + `Student`, and in the same transaction
   enqueues **two background tasks** on commit — university matching and
   timeline generation — then emails a 6-digit OTP.
2. **App → `POST /api/auth/otp/verify/`**: email + code → JWT access/refresh
   pair. This verifies the email and *is* the login.
3. **App → `POST /api/auth/password/`**: the user sets a password (onboarding
   step 3). Only then does the app route to the dashboard.
4. **Dashboard** reads `/api/profile/`, `/api/matches/`, `/api/tasks/` — by now
   the background tasks have populated matches and a dated journey plan.

---

## 3. Foundational decisions

The decisions that shaped everything else, each with the reasoning and what it
costs. Several are also pinned in persistent project memory so they survive
across working sessions.

### 3.1 Mobile app (React Native / Expo), not a PWA
- **Why.** Wayfara is meant to be a real installable app in users' hands, not a
  website. Native gives push notifications, secure keychain storage for tokens,
  and app-store presence.
- **Trade-offs.** App-store distribution and review replace "just deploy a URL";
  Apple/Google payment rules now apply (see 3.2); NativeWind v5 (preview) stands
  in for web Tailwind. iOS builds require macOS/EAS cloud — you cannot build iOS
  locally on the Linux dev machine (Android emulator + Expo Go / web cover local
  testing).
- Overrides the PRD v1.0, which specified a PWA.

### 3.2 Payments on the web via a Pakistani gateway — not IAP, not Stripe
- **Why not in-app purchase.** Apple/Google take 15–30% on digital unlocks bought
  inside a native app. Instead users buy on the **Wayfara website**, and the app
  unlocks by signing into an account that owns the entitlement (the
  Netflix/Spotify model).
- **Why not Stripe.** Stripe does not operate in Pakistan; buyers pay with local
  methods. Checkout will use a Pakistani gateway (Safepay/PayFast — SBP-licensed)
  covering **Easypaisa, JazzCash, local cards**, priced in PKR.
- **How it lands in the backend.** Unchanged in shape from a Stripe design: the
  gateway webhook flips `User.tier`. Nothing else writes `tier`.
- **Trade-offs.** To satisfy anti-steering rules the in-app UI stays neutral —
  locked content says "sign in with a Full Access account," it does **not** link
  out to a purchase page. Merchant onboarding needs Pakistani business
  registration/NTN + local bank account.

### 3.3 A dedicated, isolated PostgreSQL cluster on port 5433
- **Why.** The dev machine already runs PostgreSQL on the default **:5432**, but
  that cluster is an **intentional read-only replica of "Ash"** (a separate
  personal system) whose primary lives in Helsinki. It reports
  `pg_is_in_recovery() = t` by design.
- **Hard rule.** That :5432 cluster must **never** be modified or promoted —
  promoting detaches the replica and breaks the backup chain. Wayfara therefore
  runs its own cluster `16/finnguide` on **:5433**, database `wayfara`.
- **Trade-off.** An extra cluster to run locally, but complete isolation from an
  unrelated critical system.

### 3.4 Passwordless OTP first, password second
- **Why.** The form-first funnel (3.5) can't demand a password up front without
  becoming a register wall. So email + 6-digit OTP creates and verifies the
  account with zero friction; a password is set *after* verification, before the
  dashboard, so the account is properly secured for return logins.
- **How.** `EmailOTP` stores the hashed code (5-attempt cap, 10-min expiry);
  verify issues JWTs; `/api/auth/password/` sets the password; `/api/me/` exposes
  `has_password` so the app knows whether onboarding step 3 is done.
- **Trade-offs.** OTP delivery depends on an email provider (console backend in
  dev). Magic links were rejected in favour of codes (better on mobile).

### 3.5 Form-first onboarding, no register wall
- **Why.** Zero-friction funnel — the student sees value (their matches + a dated
  plan) before being asked to commit. `POST /api/onboarding/` is `AllowAny` and
  combines profile + email in one anonymous submission.
- **Trade-off.** The account exists before it's verified/secured, so downstream
  code treats "has a `Student` profile" and "has a password" as distinct signals.

### 3.6 Background work on Celery + Redis; tasks are thin invokers
- **Why.** Matching, timeline generation, reminders, and the nightly scraper must
  not block requests. Celery + Redis is the boring, scalable default (chosen over
  an initial django-q2 pick — migrated early rather than at scale).
- **Firm rule.** **Celery tasks contain no business logic** — they are thin
  invokers; the logic lives in service functions (`applications/services.py`,
  `students/services.py`, `scraping/services.py`). This keeps logic unit-testable
  without a broker and swappable off Celery if needed.
- **How.** Redis is shared with another local system, so Wayfara uses **db index
  5** (`redis://localhost:6379/5`). Dev/tests run `CELERY_TASK_ALWAYS_EAGER=true`
  (inline, no broker); production runs real workers + Beat for scheduling.

### 3.7 Data pipeline: nightly scraper with a tiered update policy
- **Why.** University/visa facts drift (deadlines, tuition, Migri figures). A
  2 AM (Europe/Helsinki) Celery Beat scraper keeps them fresh, but blindly
  auto-applying scraped changes to critical fields is dangerous.
- **How.** Detected changes follow a **tiered policy**: low-risk fields
  auto-apply; critical fields (deadlines, tuition, Migri figures) land in a
  **review queue** in Django admin with an email alert. The live **Opintopolku
  ingester** pulls Finland's national English-taught programme catalogue
  (konfo-backend JSON) idempotently via a stable `oid`.
- **Trade-off.** Human review adds latency to critical updates — deliberately, to
  avoid publishing a wrong tuition figure to every user.

### 3.8 Knowledge-base vs AI-layer data split
- The **scraper owns operational facts** (programmes, ECTS, deadlines where
  available). A **manual curated KB** (`UniversityProfile`) adds `world_ranking`,
  `featured`, and a `verified` flag for top universities. **City/cost-of-living
  and richer guidance live in the paid AI layer.** "Success chances" is not stored
  — it's an output of the matching engine.

### 3.9 Free AI match showcase (planned)
- When the AI layer is built, one **free** task Wayfara AI performs is picking
  **max 2–3** universities for the student's profile, shown in a **separate box
  above** the system-matched (heuristic) universities on Home. It's a free taste
  of the paid layer's value and must be its own endpoint/section — **not** folded
  into `/api/matches/`.

### 3.10 `User` / `Student` split
- Auth + entitlement (`email`, `password`, `role`, `tier`) live on `User`; the
  domain journey lives on `Student` (1:1, created lazily). `tier` stays on `User`
  because entitlement belongs to the account, is flipped only by the payment
  webhook, and must survive profile edits.

### 3.11 The 13 production layers are a standing mandate
- Every feature is checked against the [13 layers](#7-the-13-production-layers)
  from the earliest stage — new endpoint ⇒ permission + rate-limit + logging; new
  upload ⇒ storage + signed access; new query ⇒ index + cache consideration.
  Default to boring, scalable choices (stateless Django behind a load balancer,
  Postgres as source of truth, Redis for cache/queue).

---

## 4. Backend architecture

### 4.1 Stack
Django 6.0 · Django REST Framework 3.17 · djangorestframework-simplejwt 5.5 ·
psycopg 3 · PostgreSQL 16 · Celery 5 + Redis · django-celery-beat ·
django-cors-headers · Sentry SDK. Env-driven settings via `python-dotenv`;
SQLite fallback when `DATABASE_URL` is unset (a fresh clone runs with zero setup).

### 4.2 App map

Seven domain apps, split by concern:

| App | Owns | Key models |
|---|---|---|
| `accounts` | Identity, auth, entitlement, push tokens | `User`, `EmailOTP`, `DeviceToken` |
| `students` | The student journey | `Student`, `Document`, `TaskTemplate`, `Task`, `Reminder`, `Accommodation`, `Flight` |
| `universities` | Institution catalogue + curated KB | `University`, `UniversityProfile`, `Campus`, `Program` |
| `applications` | Recommendations, applications, visas, policy figures | `Match`, `Application`, `Visa`, `PolicyFigure` |
| `advisor` | Human-advisor surface (Premium) | `AdvisorThread`, `AdvisorMessage` |
| `chat` | "Ask Wayfara" AI conversations | `Conversation`, `Message` |
| `scraping` | Data-freshness pipeline | `ScrapeSource`, `ScrapeRun`, `DataChange` |

The field-level schema for the core domain lives in
[`database-schema.md`](database-schema.md). Note that doc predates `advisor`,
`scraping`, `PolicyFigure`, `UniversityProfile`, `DeviceToken`, and `EmailOTP` —
this section is the current app inventory.

### 4.3 The two engines

Both are plain service functions (invoked by Celery, per 3.6), deliberately easy
to iterate and unit-test.

- **Matching engine** (`applications/services.py`). Filters active `Program`s
  against the `Student` profile (degree level, `field_of_study` icontains,
  budget vs tuition) and scores each 0–100 with a **Safety / Good-fit / Reach**
  rating. Signals include IELTS headroom over `min_ielts_score`, acceptance-rate
  selectivity, intake match, and tuition-free bonus. Produces `Match` rows
  (distinct from `Application`, which is user *intent*). Served best-first by
  `/api/matches/`.
- **Timeline engine** (`students/services.py`). Instantiates admin-editable
  `TaskTemplate`s into per-student `Task`s with concrete `due_date`s computed
  **backwards from anchors** (intake start, application/offer deadlines, visa
  submission, arrival) using each template's `offset_anchor` + `offset_days`.
  Also generates `Reminder`s (14/7/3 days before). Regeneration preserves
  non-pending tasks. This is what makes "Migri changed a rule" a content edit,
  not a deploy.

### 4.4 Data pipeline (`scraping`)
`ScrapeSource` (a registered source + schedule) → `ScrapeRun` (one execution) →
`DataChange` (a detected diff, auto-applied or queued by `risk.py`'s tiered
policy). The Opintopolku ingester is the live source; the Migri figures scraper
is a stub pending selectors. Tuition/deadlines that sit deep in inconsistent
sources stay **admin-managed baselines** rather than being auto-scraped.

### 4.5 Auth, sessions & roles
- **JWT (SimpleJWT):** 60-min access, 30-day refresh, **rotation on** with
  **blacklist after rotation** (`token_blacklist` app). The refresh endpoint
  returns a *new pair*; the app must persist both.
- **Passwordless OTP** as the entry (3.4), password set post-verification.
- **Roles.** `User.role` is `student` or `advisor`. `/api/me/` is the session
  bootstrap — it returns `role`, `tier`, `email_verified`, `has_password`, and
  `onboarding_complete`, and the app routes on those (student dashboard vs
  advisor console, and which onboarding step remains).
- **Logout** blacklists the refresh token and drops the device's push token.
- **Push:** `DeviceToken` stores Expo push tokens per device; advisor replies and
  reminders notify via Expo's push service.

### 4.6 API surface

All under `/api/`. Auth required unless marked **(anon)**.

| Method + path | Purpose |
|---|---|
| `POST /onboarding/` **(anon)** | Get Started form → account + Student + background matching/timeline + OTP |
| `POST /auth/otp/request/` **(anon)** | Send login/verification code (always 200; no enumeration) |
| `POST /auth/otp/verify/` **(anon)** | email + code → JWT pair (verifies email; is the login) |
| `POST /auth/token/refresh/` **(anon)** | Rotate the refresh token → new pair |
| `POST /auth/password/` | Set/replace the account password (onboarding step 3) |
| `GET /me/` | Session bootstrap (role, tier, verified, has_password, onboarding_complete) |
| `POST /auth/logout/` | Blacklist refresh token + drop device push token |
| `POST /devices/` | Register an Expo push token |
| `GET\|PATCH /profile/` | Read/update the onboarding profile |
| `GET /matches/` | University recommendations, best fit first |
| `GET /tasks/` (`?phase=N`) · `POST /tasks/<id>/status/` | Journey plan + status changes |
| `GET /universities/` · `GET /universities/<id>/` | Catalogue (cached) |
| `advisor/*`, `my-advisor/messages/` | Advisor console + the student side of the thread (Premium-gated) |

> `POST /auth/register/` (password registration) exists but is **not** the app's
> entry point — onboarding + OTP is. It remains for admin/testing.

### 4.7 Security posture
- **Row-level scoping.** Student-owned models use a manager (`owned_by` /
  `StudentOwnedManager`) so every query is scoped to the requesting user; advisor
  views are scoped to assigned students only.
- **Rate limiting.** DRF scoped throttles per sensitive endpoint (onboarding,
  otp_request, otp_verify, set_password, register, advisor_activate) plus a
  per-target-inbox OTP cap that survives IP rotation. Relaxed automatically under
  `TESTING`.
- **Transport controls.** `CORS_ALLOWED_ORIGINS` and `ALLOWED_HOSTS` are
  env-driven (dev defaults to localhost). Native app traffic isn't subject to
  CORS; the web build is, so LAN/production origins must be whitelisted.
- **Not yet set** (deploy-time, Layer 8): `SECURE_SSL_REDIRECT`, HSTS, secure
  cookie flags — these light up when a real host + TLS exist.

---

## 5. Mobile architecture

### 5.1 Stack
Expo SDK **57** · React Native 0.86 · React 19.2 · NativeWind v5 (preview) ·
React Navigation (native stack) · `expo-secure-store` · `expo-linear-gradient` ·
`react-native-svg` · Google Fonts (Manrope + Space Grotesk). Web target via
`react-native-web` for fast local preview.

### 5.2 Structure

```
mobile/
  App.tsx            # font loading + AuthProvider + auth-gated navigator
  app.config.js      # dynamic config; apiUrl from WAYFARA_API_URL env (deploy-ready)
  theme/             # design tokens (coral accent, cream canvas, type, radii)
  components/        # icons (SVG), ui (Wordmark/buttons/chips), form (Field/ChoiceRow)
  context/AuthContext.tsx   # session state machine + refresh hook
  lib/api.ts         # typed API client (transport only)
  lib/tokenStorage.ts# JWTs in keychain (native) / localStorage (web)
  navigation/types.ts# typed route params
  screens/           # Welcome, GetStarted, Login, VerifyOtp, CreatePassword, Home
```

### 5.3 Session model
`AuthContext` is a small state machine driving the root navigator:

| Status | Meaning | Route |
|---|---|---|
| `loading` | session bootstrap in flight (stored tokens + `/me/`) | splash |
| `signedOut` | no valid session | Welcome → GetStarted → Login → VerifyOtp |
| `needsPassword` | verified but `has_password === false` | CreatePassword (isolated) |
| `signedIn` | full account | Home |

Tokens live in a ref (read synchronously per request) and in secure storage. The
API client registers a **refresh-on-401 hook** (`configureApi`): a 401 triggers
one refresh + retry; failure clears the session. Token **rotation** means each
refresh persists a new pair.

### 5.4 API client (`lib/api.ts`)
Transport-only, typed against the DRF serializers. `defaultApiUrl()` reads
`Constants.expoConfig.extra.apiUrl` (set from `WAYFARA_API_URL` at build time),
falling back to `10.0.2.2:8000` (Android emulator → host) or `localhost:8000`.
`ApiError` surfaces DRF messages; refresh/persistence live in `AuthContext`, not
here.

### 5.5 Design system
Coral-first brand (`#F8593C`, with amber/terracotta variants) on a warm cream
canvas, Space Grotesk (display) + Manrope (body). The **Pin Waypoint** logo — a
destination pin carrying a five-waypoint "W" route — is the app mark and the
launcher/splash/favicon set. All tokens centralized in `theme/`; screens
reference them rather than hardcoding hex.

---

## 6. Configuration & environments

Everything environment-specific is an env var — nothing host-specific is
hardcoded, which is what makes the eventual Railway deploy a config change, not a
code change.

### Backend (`backend/.env`)
| Var | Purpose | Dev default |
|---|---|---|
| `DATABASE_URL` | Postgres DSN | SQLite fallback if unset; real dev → `:5433/wayfara` |
| `DJANGO_DEBUG` | debug mode | `true` |
| `DJANGO_ALLOWED_HOSTS` | Host header allowlist | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | web origins | `localhost:8081,localhost:19006` |
| `REDIS_URL` | Celery broker/result | `redis://localhost:6379/5` |
| `CELERY_TASK_ALWAYS_EAGER` | run tasks inline | `true` (dev/test) |
| `DJANGO_EMAIL_BACKEND` | OTP delivery | console backend (codes print to the server log) |
| `SENTRY_DSN` | error tracking | unset (Sentry activates only in prod) |

### Mobile (`app.config.js`)
| Var | Purpose | Dev default |
|---|---|---|
| `WAYFARA_API_URL` | backend base URL baked into `extra.apiUrl` | `http://localhost:8010` |
| `REACT_NATIVE_PACKAGER_HOSTNAME` | pin Metro to a specific LAN IP | auto |

### Local dev notes
- **Backend port.** The dev machine's :8000 is taken by an unrelated system, so
  Wayfara's Django dev server runs on **:8010** and `WAYFARA_API_URL` points
  there.
- **OTP in dev.** The console email backend prints codes to the Django log rather
  than sending mail — grep the server log for the 6-digit code.
- **Physical-device testing (Expo Go).** Public Expo Go tracks the *latest*
  released SDK; SDK 57 (bleeding edge, incl. NativeWind v5 preview) may be ahead
  of it, so Expo Go can refuse the project. Options: (a) view the **web build**
  on the phone's browser over LAN, (b) an **Android emulator** (local, uses your
  own SDK), or (c) an **EAS dev build** for the real iPhone (needs an Apple
  Developer account; no Mac required). iOS cannot be built locally on Linux.
- **LAN testing recipe.** Bind Django to `0.0.0.0`, add the laptop's LAN IP to
  `DJANGO_ALLOWED_HOSTS` **and** (for the web build) `CORS_ALLOWED_ORIGINS`, set
  `WAYFARA_API_URL=http://<LAN-IP>:8010`, and pin Metro with
  `REACT_NATIVE_PACKAGER_HOSTNAME`. Clear Metro cache (`--clear`) after changing
  the API URL or the old value stays baked into the web bundle.

---

## 7. The 13 production layers

Awais's mandated launch-readiness checklist. Status as of this document:

| # | Layer | Status | Where it lives |
|---|---|---|---|
| 1 | Frontend foundations | 🟢 | Nav, auth state, secure token storage, typed API client, onboarding spine, design system |
| 2 | APIs & backend logic | 🟢 | 7 apps; matching + timeline engines; advisor; scraper |
| 3 | Database & storage | 🟡 | Postgres :5433 + migrations done; **media still local disk** (needs S3/R2 + signed access) |
| 4 | Auth & permissions | 🟢 | JWT + OTP + password step; roles; row-level scoping |
| 5 | Hosting & deployment | 🔴 | Not started (Railway planned; env-driven config already prepped) |
| 6 | Cloud & compute | 🟡 | Celery/Redis/Beat designed & correct; runs only locally |
| 7 | CI/CD & version control | 🟡 | GitHub Actions CI (Postgres service); **no CD** (blocked on Layer 5) |
| 8 | Security & RLS | 🟡 | App-layer scoping done; `SECURE_*`/HSTS/cookie flags are deploy-time |
| 9 | Rate limiting | 🟢 | DRF scoped throttles + per-inbox OTP cap |
| 10 | Caching & CDN | 🟡 | Redis cache + cached discovery API; **CDN untouched** (no static/media host yet) |
| 11 | Load balancing & scaling | 🔴 | Stateless design honoured; nothing to balance yet (blocked on Layer 5) |
| 12 | Error tracking & logs | 🟢 | Sentry + Sentry Logs (WARNING+), env-gated |
| 13 | Availability & recovery | 🟡 | `backup_db.sh` exists; **no tested restore / uptime monitoring** |

**Reading the board:** the two reds plus the yellow halves of 6/7/8/10/13 are
largely gated by **one decision — picking a host (Railway)**. Deploying lights up
TLS/`SECURE_*`, CD, a load-balancer path, CDN, and a place to point uptime
monitoring. The genuinely host-independent gaps are **Layer 3 storage** (S3/R2
before any real document upload ships) and **Layer 1 breadth** (feature screens
beyond the onboarding spine).

---

## 8. Trade-offs & known debt

Consolidated, so nothing hides in prose:

1. **Media on local disk (Layer 3).** `Document.file` and advisor audio write to
   `media/`. The most sensitive payload (passports, transcripts) needs S3/R2 +
   signed URLs before any real upload feature. **Highest quiet risk.**
2. **Production API URL is deploy-time.** `app.config.js` defaults `apiUrl` to
   `localhost:8010`. A shipped build **must** get `WAYFARA_API_URL` set to the
   real HTTPS host or every API call fails on-device — this is about the
   `localhost`, not the port.
3. **NativeWind v5 is preview software.** Works today; fallback is pinning a
   known-good nightly. Also the reason SDK 57 may outrun public Expo Go.
4. **`grades` isn't yet a matching signal.** Collected in onboarding, stored, but
   the scoring heuristic doesn't weight it. Product decision pending.
5. **Field-of-study taxonomy is hardcoded in the app.** The onboarding form's
   field chips (IT/Business/Design/Engineering) must match the Opintopolku
   catalogue's values; a `/api/fields/` endpoint would remove the duplication.
6. **Migri figures are stubbed / snapshotted.** The scraper's Migri source is a
   stub; `Visa.funds_required_eur` and `PolicyFigure` are snapshots that need
   verification against Migri's current numbers before Phase 4 content ships.
7. **Payment layer not built.** `User.tier` is webhook-driven by design, but the
   `Payment` model + gateway integration land later (with merchant onboarding).
8. **Advisor-tap sign-out footgun (app).** Home's avatar currently signs out on
   tap — a stand-in until a real Profile tab exists.

---

## 9. Roadmap & open items

Near-term, roughly ordered:

1. **Layer 1 breadth** — Profile tab (+ deliberate sign-out), the Explore/Apps/
   Chat tabs, in-app push registration, and the advisor/messaging surface.
2. **Layer 3 storage** — S3/R2 + signed access, before document upload UI.
3. **Hosting (Layer 5, when ready)** — Railway: set the env vars above, get TLS +
   the `SECURE_*` settings, wire CD, point uptime monitoring. Unblocks ~5 layers.
4. **Payments (Week 9)** — `Payment` model, Pakistani gateway webhook → `tier`.
5. **AI layer** — "Ask Wayfara" over `chat`, document AI review (Premium), and the
   free [AI match showcase](#39-free-ai-match-showcase-planned).
6. **Data pipeline hardening** — real Migri selectors; verify snapshot figures.

Open questions to revisit: migrations vs first deploy target; NativeWind v5
stable; Pakistani gateway merchant onboarding (needs business docs); a
`/api/fields/` endpoint for the onboarding taxonomy.
