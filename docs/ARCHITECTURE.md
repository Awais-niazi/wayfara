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
| `backend/` | REST API, business logic, AI orchestration, data pipeline | Django 6 · DRF · Supabase-verified JWTs · PostgreSQL 16 · Celery/Redis |
| `mobile/` | The installable app | Expo (React Native, SDK 57) · NativeWind v5 · React Navigation |
| `web/` | Landing page + purchase front door | Static HTML (checkout wiring lands later) |
| `docs/` | Architecture, schema, build logs | Markdown |

### Shape of the system

```
  ┌──────────────────────┐  signup / login / OTP / refresh
  │  Supabase Auth       │ ◀──────────────────────────────┐
  │  (identity authority)│ ── session (ES256 JWT) ──────▶ │
  └──────────────────────┘                                │
                                                          │
  ┌─────────────┐        HTTPS / JSON        ┌────────────┴─────────────┐
  │  Mobile app │ ───────────────────────▶  │  Django REST API          │
  │  (Expo RN)  │   Bearer: Supabase JWT     │  (verifies via JWKS;      │
  │             │ ◀───────────────────────  │   stateless, scalable)    │
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
                                          │  reminders · monthly scraper  │
                                          └───────────────────────────────┘
```

### Request lifecycle (the onboarding spine)

The canonical flow the whole system is built around — **form-first, no register
wall** (the account fields are just step 1 of the same wizard):

1. **App → Supabase `signUp`** (email + password, collected with the student's
   first/last name in wizard step 1). Supabase emails a **6-digit code**; the app verifies it with
   Supabase (`verifyOtp`) and now holds a session (ES256 access + refresh,
   auto-refreshed by supabase-js).
2. **App → `POST /api/v1/onboarding/`** (authenticated with that token): records
   the student's **name** and stores the `Student` profile; in the same transaction
   enqueues **two background tasks** on commit — university matching and
   timeline generation. Django JIT-provisions its local `User` shadow (keyed by
   the Supabase UUID) the first time it sees a valid token.
3. **Dashboard** reads `/api/v1/profile/`, `/api/v1/matches/`,
   `/api/v1/tasks/` — by now the background tasks have populated matches and
   a dated journey plan. The greeting uses the first name.

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

### 3.4 Supabase as the identity authority (July 2026)
- **Why.** Auth is a foundation, not a feature — credentials, sessions, OTP
  delivery, and token issuance are now owned by a dedicated, audited provider
  (Supabase Cloud, Singapore region; GoTrue is open-source and self-hostable, so
  there's an exit). Alternatives weighed: Clerk (best DX, MAU-priced — wrong
  economics for a price-sensitive B2C market), Firebase (Google lock-in),
  WorkOS (B2B SSO, wrong tool).
- **How.** The app talks to Supabase directly (`mobile/lib/supabase.ts`):
  `signUp` (email + password), `signInWithPassword`, `signInWithOtp` (the
  fallback login), `verifyOtp`, `signOut`. Django never issues tokens — it only
  *verifies* the forwarded access token
  (`accounts/authentication.py::SupabaseJWTAuthentication`): ES256 against the
  project's public **JWKS** endpoint (cached), with an HS256 fallback for
  legacy shared-secret projects; the token's own header picks the path. On
  first valid token, the local `User` shadow is **JIT-provisioned**, keyed by
  `supabase_id` (the Supabase UUID); a pre-provisioned row (advisor) is linked
  by email instead of duplicated. Django keeps what Supabase can't own:
  the person's name, `role`, `tier`, and the whole domain.
- **Email delivery.** Supabase Auth sends via **custom SMTP (Resend)**; the
  Confirm-signup and Magic-link templates are edited to carry `{{ .Token }}` —
  a 6-digit code, not a link (codes beat links on mobile). Until a sending
  domain is verified in Resend, mail only delivers to the Resend account's own
  address (fine for dev; domain verification is a launch prerequisite).
- **History.** Replaces the home-grown layer (hashed `EmailOTP` +
  SimpleJWT issue/rotate/blacklist, removed in the same change). Pre-launch,
  so a clean cutover: no user migration, old test accounts deleted.

### 3.5 Form-first onboarding, no register wall
- **Why.** Zero-friction funnel — the student sees value (their matches + a dated
  plan) before being asked to commit. The account fields (email, **first/last
  name**, password) are step 1 of the same 4-step wizard, not a separate wall; the
  profile answers ride along and `POST /api/v1/onboarding/` (authenticated)
  stores them once the email code verifies.
- **Trade-off.** A Supabase identity can exist before onboarding finishes, so
  the app treats "has a session" and "has a `Student` profile"
  (`onboarding_complete` on `/me/`) as distinct signals — a half-finished
  wizard resumes rather than dead-ending.

### 3.6 Background work on Celery + Redis; tasks are thin invokers
- **Why.** Matching, timeline generation, reminders, and the monthly scraper must
  not block requests. Celery + Redis is the boring, scalable default (chosen over
  an initial django-q2 pick — migrated early rather than at scale).
- **Firm rule.** **Celery tasks contain no business logic** — they are thin
  invokers; the logic lives in service functions (`applications/services.py`,
  `students/services.py`, `scraping/services.py`). This keeps logic unit-testable
  without a broker and swappable off Celery if needed.
- **How.** Redis is shared with another local system, so Wayfara uses **db index
  5** (`redis://localhost:6379/5`). Dev/tests run `CELERY_TASK_ALWAYS_EAGER=true`
  (inline, no broker); production runs real workers + Beat for scheduling.
- **Role boundary (firm).** Redis is **transport and cache** — the Celery broker
  (db 5), the version-keyed catalog cache and throttle counters (db 6). Postgres
  holds **anything that must survive, be audited, or be human-reviewed** — which
  is why scraped diffs stage in the `DataChange` table, not a Redis queue: staged
  critical changes can wait days for admin review, and a queue's durability and
  queryability are wrong for that. (Considered and rejected July 2026.)

### 3.7 Data pipeline: monthly scraper with a tiered update policy
- **Why.** University/visa facts drift (deadlines, tuition, Migri figures). A
  Celery Beat scraper (**02:00 Europe/Helsinki on the 1st of each month** — the
  catalogue changes on academic-cycle cadence, not nightly, and monthly keeps
  our konfo load polite) keeps them fresh, but blindly auto-applying scraped
  changes to critical fields is dangerous.
- **How.** Detected changes follow a **tiered policy**: low-risk fields
  auto-apply; critical fields (deadlines, tuition, Migri figures) land in a
  **review queue** in Django admin with an email alert. First-time population of
  an *empty* field auto-applies even when critical — the gate is on **changing**
  a value a student may already rely on. The live **Opintopolku ingester** pulls
  Finland's national English-taught programme catalogue (konfo-backend JSON)
  idempotently via a stable `oid`.
- **Trade-off.** Human review adds latency to critical updates — deliberately, to
  avoid publishing a wrong tuition figure to every user. Monthly cadence means a
  mid-cycle deadline change can lag up to a month; the mitigation is a manual
  `run_scraper_task` (or admin edit) when a change is known.

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
  into `/api/v1/matches/`.

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

### 3.12 API versioning: everything lives under `/api/v1/` (July 2026)
- **Why.** Before this, every route hung directly off `/api/`. That's fine with
  one client you control, but it's a trap the moment the app is in app stores:
  a breaking change then has no way to roll forward without either stranding
  old app builds or permanently constraining new ones to old behavior.
- **How.** `wayfara/urls.py` defines one constant, `API_V1 = "api/v1/"`, and
  every app's `include()` is prefixed with it — there's no code path that
  registers an endpoint outside the version by accident. `/admin/` and
  `/healthz` are the only routes that intentionally sit outside it (see 3.13).
  A future breaking change gets `api/v2/` alongside `v1`, not a replacement —
  `v1` stays live until every client has migrated.
- **Enforced, not just documented.** `wayfara/tests_conventions.py::URLVersioningTests`
  walks the root `urlpatterns` and fails CI if any top-level route isn't under
  `admin/`, `healthz`, or `api/v1/`. A future session (human or Claude) that
  reflexively adds `path("api/", include(...))` gets caught immediately, not
  discovered after ship.
- **Client-side.** The mobile client (`mobile/lib/api.ts`) prepends the version
  once in `request()` via `API_VERSION_PREFIX`; every call site passes just the
  resource path (`"/me/"`, not `"/api/me/"`), so a version bump is a one-line
  change, not a find-and-replace across the file.

### 3.13 `/healthz`: unauthenticated, unversioned, infra-only
- **Why.** Layer 5 (hosting) and Layer 11 (load balancing) both need something
  to ping that isn't gated by JWT auth or API versioning — Railway's health
  check, a future load balancer, and any uptime monitor all expect one stable
  path that never changes shape.
- **How.** `wayfara/views.py::HealthCheckView` — no authentication, no
  permission beyond `AllowAny`, no throttling (infra hits this every few
  seconds; it shouldn't burn throttle budget or get rate-limited). It checks
  the two synchronous dependencies a request actually needs — Postgres and the
  Redis cache — and returns `200 {"status": "ok", "checks": {...}}` or
  `503 {"status": "unhealthy", ...}`. Deliberately does **not** check the
  Celery broker: a slow background queue isn't the same failure mode as "can't
  serve requests," and coupling them would page someone for the wrong reason.
- **Placement.** Lives at the bare path `/healthz`, outside `/api/v1/` entirely
  — infra endpoints shouldn't move when the API version does.

### 3.14 Strict input validation: reject unknown fields, don't discard them
- **Why.** DRF's default behavior silently drops any request key a serializer
  doesn't declare. That's convenient but means a typo, a stale client field
  after a rename, or a mass-assignment probe against an undeclared field
  vanishes without a trace instead of failing loudly. An endpoint is designed
  to take specific data; anything else should be rejected, not swallowed.
- **How.** `wayfara/serializers.py` defines `StrictSerializer` and
  `StrictModelSerializer` — every serializer in the codebase inherits one of
  these instead of DRF's plain `Serializer`/`ModelSerializer`. Their shared
  `to_internal_value` diffs the request payload's keys against the declared
  field set and raises a 400 naming every field it doesn't recognize.
- **What this deliberately does NOT change.** A declared-but-`read_only` field
  submitted by the client (e.g. PATCHing `/api/v1/profile/` with a stray
  `"tier": "premium"`) is still silently ignored, not rejected — that's DRF's
  existing, correct field-level access control, and changing it would break
  any client that round-trips a full object back on PATCH. The strict layer
  targets keys the serializer has never heard of, not read-only ones it has.
- **Enforced, not just documented.** `wayfara/tests_conventions.py::StrictSerializerConventionTests`
  imports every local app's `serializers` module and fails CI if any serializer
  class defined there isn't a `Strict*` subclass — the same mechanism that
  makes 3.12 durable against a future session forgetting the rule.
- **Output.** Every `ModelSerializer.Meta.fields` in the codebase is an
  explicit list — none use `fields = "__all__"` — so response shape was
  already whitelisted by construction; this pass didn't need to change that.

---

## 4. Backend architecture

### 4.1 Stack
Django 6.0 · Django REST Framework 3.17 · PyJWT + cryptography (Supabase token
verification) · psycopg 3 · PostgreSQL 16 · Celery 5 + Redis · django-celery-beat ·
django-cors-headers · Sentry SDK. Env-driven settings via `python-dotenv`;
SQLite fallback when `DATABASE_URL` is unset (a fresh clone runs with zero setup).

### 4.2 App map

Eight domain apps, split by concern:

| App | Owns | Key models |
|---|---|---|
| `accounts` | Identity mirror (Supabase-keyed), entitlement, push tokens | `User`, `DeviceToken` |
| `students` | The student journey | `Student`, `Document`, `TaskTemplate`, `Task`, `Reminder`, `Accommodation`, `Flight` |
| `universities` | Institution catalogue + curated KB | `University`, `UniversityProfile`, `Campus`, `Program` |
| `applications` | Recommendations, applications, visas, policy figures | `Match`, `Application`, `Visa`, `PolicyFigure` |
| `advisor` | Human-advisor surface (Premium) | `AdvisorThread`, `AdvisorMessage` |
| `chat` | "Ask Wayfara" AI conversations | `Conversation`, `Message` |
| `scraping` | Data-freshness pipeline | `ScrapeSource`, `ScrapeRun`, `DataChange` |
| `notifications` | Notification platform (inbox + push, all sources) | `Notification`, `Broadcast` |

The field-level schema for the core domain lives in
[`database-schema.md`](database-schema.md). Note that doc predates `advisor`,
`scraping`, `PolicyFigure`, `UniversityProfile`, and `DeviceToken` —
this section is the current app inventory.

### 4.3 The two engines

Both are plain service functions (invoked by Celery, per 3.6), deliberately easy
to iterate and unit-test.

- **Matching engine** (`applications/services.py`). Filters active `Program`s
  against the `Student` profile (degree level, `field_of_study` icontains,
  budget vs tuition, **application window still open** — a passed
  `application_deadline` disqualifies outright; unknown deadlines stay) and
  scores each 0–100 with a **Safety / Good-fit / Reach** rating. Signals
  include IELTS headroom over `min_ielts_score`, **academic strength**
  (grade-band boost: exceptional +25 / strong +15 / good +8 — see debt #4,
  resolved), acceptance-rate selectivity, intake match, and tuition-free
  bonus. The score is a **profile-fit heuristic, not an admission
  probability**. Produces `Match` rows (distinct from
  `Application`, which is user *intent*). Served best-first by
  `/api/v1/matches/`. Accuracy rules (July 2026 scan):
  - **Budget:** blank and `0` both mean *tuition-free only* (the validator's
    contract); a positive budget uses `lte`, which also drops **null-fee**
    programs — affordability is never promised for an unknown price.
  - **English score** is normalised to an **IELTS band via a concordance
    table** (`_ielts_equivalent`) before comparison — without that a TOEFL 100
    would parse as "100" and clear every requirement. A lingering score is
    **not credited** when `language_test_status` is booked/not-taken.
  - **Re-match on profile edit:** `PATCH /profile/` re-runs matching (on
    commit) when any engine-read field changed (`MATCH_RELEVANT_FIELDS` in
    `students/views.py`) — the match list always describes the *current*
    profile; name-only edits don't churn it. Tested in `applications/tests.py`.
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

**Run mechanics** (July 2026 optimization pass):
- **Two-phase scrape.** Phase 1 gathers all search hits (9 keyword queries);
  phase 2 fans the per-programme detail enrichment (2 HTTP calls each) out over
  a **thread pool** (`enrich_workers = 8`). Enrichment is deliberately **pure
  HTTP + parsing** — all ORM work (university/campus resolution, memoized per
  run; diffing; commits) stays on the main thread, so no per-thread DB
  connections exist. `map()` preserves hit order, keeping commits deterministic.
  Measured: 285 programmes reconcile in ~37s against live konfo.
- **Connection pooling.** One `requests.Session` per thread (keep-alive) instead
  of a fresh TLS handshake per request.
- **Incremental commits.** Each record commits in its own short transaction — a
  long ingest keeps its progress if it dies, and DB locks stay brief.
- **Stale-run janitor.** `fail_stale_runs()` runs before each scrape and marks
  runs stuck in RUNNING past the 30-min Celery hard cap as FAILED, so a killed
  worker can't leave phantom "running" audit rows.
- **Cache coherence.** Any ORM write to a catalog model (scraper create, applied
  `DataChange`, admin edit) fires the `universities/signals.py` post-save hook,
  which bumps the version key the cached catalog API is keyed on — approved
  changes are visible to users immediately, no TTL wait.

### 4.4b Notification platform (July 2026)

One spine, many sources. Every notification in the product goes through
`notifications/services.py::notify(user, category, title, body, data)` —
which writes a durable `Notification` inbox row and mirrors it as an Expo
push (`accounts/push.py`). The row is the record; a missed push is never a
lost message. Adding a source is one call, never new plumbing.

- **Sources wired:** the reminder dispatcher (Celery Beat every 5 min,
  `setup_notification_schedule`; claim-then-send so overlapping runs can't
  double-send; reminders >24h past due are swallowed + logged, so an outage
  never blasts stale pings), admin-composed `Broadcast`s (targeted: all /
  intake year / matched university; draft-only send guard), scraper-approved
  **critical** `DataChange`s (notify students matched to the affected
  university; low-risk auto-applies stay silent), and advisor messages.
- **API:** `GET /notifications/` (paged, `unread_count` in-band for the bell
  badge), `POST /notifications/read/` — owner-scoped.
- **Mobile:** push registration on sign-in (permission → Expo token →
  `POST /devices/`; token pruned on sign-out; web/simulators no-op),
  `NotificationsScreen` inbox, live unread badge on the Home bell.
- **Future phases plug into `notify()`:** doc-verification/application/visa
  events (categories reserved), AI world news, per-category preferences +
  quiet hours + email channel — all single-point changes.
- **Limitation:** real push delivery requires a physical device with a dev
  build (Expo Go dropped Android remote push in SDK 53); the inbox is the
  web-testable surface.

### 4.5 Auth, sessions & roles
- **Supabase owns sessions** (3.4): ES256 access tokens (1-hr expiry) +
  refresh, rotated automatically by supabase-js. Django holds no session state
  and no token blacklist — revocation is Supabase's `signOut()`.
- **Verification, not issuance.** `SupabaseJWTAuthentication` is the sole DRF
  auth class: Bearer token → JWKS (or legacy HS256) signature check →
  `aud=authenticated` + expiry → local `User` by `supabase_id`
  (JIT-provisioned). Rate-limiting bad tokens is unnecessary — a forged
  signature fails in microseconds with no DB touch.
- **Two login paths for returning users.** Email + password
  (`signInWithPassword`) is primary; "email me a code" (`signInWithOtp`,
  `shouldCreateUser: false` so login can't silently create accounts) is the
  fallback. Passwords are 8–20 chars — enforced in the wizard and in
  Supabase's minimum-length setting.
- **Names, not usernames (July 2026).** Onboarding requires first + last
  name (stored on `User`, editable via `PATCH /profile/`); the dashboard
  greets **"Welcome aboard, {first name}"**. A separate unique username was
  collected briefly, then dropped the same month — one less thing to invent
  at signup, and a name is what an advisor/greeting actually needs.
- **Roles.** `User.role` is `student` or `advisor`. `/api/v1/me/` is the session
  bootstrap — it returns `first_name`, `role`, `tier`, `email_verified`, and
  `onboarding_complete`, and the app routes on those.
- **Advisor provisioning.** No self-signup: `manage.py create_advisor <email>`
  (or the admin action) calls Supabase's Admin **invite** endpoint with the
  service-role key — the advisor sets their own password via Supabase's invite
  email; the admin never holds it — and mirrors a local
  `User(role=advisor, supabase_id=…)`. On first login the auth class links by
  `supabase_id`, so the advisor role is never reset by JIT defaults. (The old
  Django reset-token activation flow is gone with the rest of the home-grown
  layer.)
- **Logout** = Supabase `signOut()` client-side; `POST /auth/logout/` remains
  only to prune the device's push token.
- **Push:** `DeviceToken` stores Expo push tokens per device; advisor replies and
  reminders notify via Expo's push service.

### 4.6 API surface

All under `/api/v1/` (3.12), and all require a Supabase bearer token — signup,
login, OTP, and token refresh happen **against Supabase directly**, so Django
no longer exposes any anonymous auth endpoints.

| Method + path | Purpose |
|---|---|
| `POST /onboarding/` | Get Started wizard → records name + stores Student + background matching/timeline |
| `GET /me/` | Session bootstrap (first_name, role, tier, verified, onboarding_complete) |
| `POST /auth/logout/` | Prune this device's push token (session revocation is Supabase `signOut()`) |
| `POST\|DELETE /devices/` | Register / deregister an Expo push token |
| `GET\|PATCH /profile/` | Read/update the onboarding profile (incl. name); match-relevant edits re-run matching |
| `GET /matches/` | University recommendations, best fit first |
| `GET /tasks/` (`?phase=N`) · `POST /tasks/<id>/status/` | Journey plan + status changes |
| `GET /universities/` · `GET /universities/<id>/` | Catalogue (cached, public) |
| `GET /notifications/` · `POST /notifications/read/` | In-app inbox (paged, unread count) + mark-read |
| `POST\|GET /applications/` · `GET\|PATCH /applications/<id>/` · `POST .../status/` | Application workspace: create from match, checklist, SOP, status ladder (milestones notify) |
| `POST\|GET /documents/` · `DELETE /documents/<id>/` · `GET .../download/` | Student document pool: capped multipart upload, owner-scoped signed-URL download |
| `advisor/*`, `my-advisor/messages/` | Advisor console + the student side of the thread (Premium-gated) |

> `GET /healthz` (bare path, outside `/api/v1/`, unauthenticated) is the only
> exception — see 3.13.

### 4.7 Security posture
- **Row-level scoping.** Student-owned models use a manager (`owned_by` /
  `StudentOwnedManager`) so every query is scoped to the requesting user; advisor
  views are scoped to assigned students only.
- **Rate limiting.** Global anon/user throttles plus a scoped `onboarding`
  rate; credential-stuffing and OTP-flood limiting moved to Supabase with the
  endpoints themselves (its Auth rate limits + Resend). Relaxed automatically
  under `TESTING`.
- **Input hardening (July 2026).** Every writable field is bounded and typed at
  the serializer, so hostile input fails with a clean 400 before it reaches the
  ORM or DB (names are length-capped; passwords — now validated by
  Supabase — stay 8–20 chars, mirrored in its min-length setting). SQL
  injection was never reachable — the codebase has **zero raw SQL** (`grep`
  for `.raw(`/`.extra(`/`cursor()` is empty; everything is parameterized ORM) —
  so these caps are defense-in-depth, not the primary control.
- **Semantic validation (July 2026).** Beyond format/length, the academic
  fields are checked for real-world sanity in `students/validators.py` (shared
  by onboarding + profile): a test score must be in range for its test type
  (IELTS 0–9 half-steps, TOEFL 0–120, PTE 10–90, Duolingo 10–160), a grade must
  fit its declared scale (GPA 0.5–4, % 0–100, letter A–E±), and a budget must be
  plausible (blank/0 = tuition-free, else €1k–€100k). The mobile wizard mirrors
  these client-side for instant feedback; the serializer is the authority.
- **Credentials at rest are Supabase's problem (July 2026).** With the move to
  Supabase (3.4), Django stores **no passwords and no OTP codes** — the local
  `User.password` is unusable for app users. (The previous home-grown layer's
  hashed-OTP/constant-time-compare hardening went with it; the lesson is
  encoded in 3.4's "why".)
- **Config fail-fast (July 2026).** The app **refuses to boot** with
  `DEBUG=False` if `DJANGO_SECRET_KEY` is the dev fallback, if `SUPABASE_URL`
  is unset (nothing could authenticate), or if email is still on the console
  backend (mail would be silently dropped, and OTP is a login path) — broken
  deploys are impossible rather than silent.
- **Transport controls.** `CORS_ALLOWED_ORIGINS` and `ALLOWED_HOSTS` are
  env-driven (dev defaults to localhost). Native app traffic isn't subject to
  CORS; the web build is, so LAN/production origins must be whitelisted.
- **Transport security (Layer 8), defined and gated on `DEBUG` (July 2026).**
  With `DEBUG=False` the app enables `SECURE_SSL_REDIRECT`, HSTS (1 yr,
  subdomains, preload), `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`,
  `SECURE_CONTENT_TYPE_NOSNIFF`, and trusts a proxy's `X-Forwarded-Proto`.
  `manage.py check --deploy` is clean but for the key-length notice on a dummy
  key. Local HTTP dev is untouched (all flags off while `DEBUG=True`).

---

## 5. Mobile architecture

### 5.1 Stack
Expo SDK **57** · React Native 0.86 · React 19.2 · NativeWind v5 (preview) ·
React Navigation (native stack) · `@supabase/supabase-js` (+ AsyncStorage,
URL polyfill) · `expo-linear-gradient` · `react-native-svg` · Google Fonts
(Manrope + Space Grotesk). Web target via `react-native-web` for fast local
preview.

### 5.2 Structure

```
mobile/
  App.tsx            # font loading + AuthProvider + auth-gated navigator
  app.config.js      # dynamic config; apiUrl + Supabase URL/anon key from env
  .env               # SUPABASE_URL + SUPABASE_ANON_KEY (gitignored; Expo auto-loads)
  theme/             # design tokens (coral accent, cream canvas, type, radii)
  components/        # icons (SVG), ui (Wordmark/buttons/chips), form (Field/ChoiceRow)
  context/AuthContext.tsx   # session state derived from Supabase + /me/
  lib/supabase.ts    # Supabase client (AsyncStorage-persisted, auto-refresh)
  lib/api.ts         # typed API client (transport only; token from Supabase)
  navigation/types.ts# typed route params
  screens/           # Welcome, GetStarted, Login, VerifyOtp, Home, …
```

### 5.3 Session model
Supabase owns the session (persisted in AsyncStorage, auto-refreshed by
supabase-js); `AuthContext` derives the route from two facts — is there a
session, and has onboarding finished (`/me/.onboarding_complete`):

| Status | Meaning | Route |
|---|---|---|
| `loading` | session bootstrap in flight (`getSession()` + `/me/`) | splash |
| `signedOut` | no session, **or** session without a finished profile | Welcome → GetStarted → Login → VerifyOtp |
| `signedIn` | session + onboarded | Home |

The "session but not onboarded" case staying in the signed-out stack is what
lets a half-finished wizard resume instead of being yanked to a dead dashboard.
`onAuthStateChange` recomputes the route on every sign-in/out/refresh.

### 5.4 API client (`lib/api.ts`)
Transport-only, typed against the DRF serializers. Each request reads the
current Supabase access token (`supabase.auth.getSession()`) and sends it as
the Bearer credential; on a 401 it asks Supabase to `refreshSession()` once
and retries. `defaultApiUrl()` reads `Constants.expoConfig.extra.apiUrl` (set
from `WAYFARA_API_URL` at build time), falling back to `10.0.2.2:8000`
(Android emulator → host) or `localhost:8000`. `ApiError` surfaces DRF
messages.

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
| `DJANGO_SECRET_KEY` | signing key | dev fallback; **required** when `DEBUG=False` (app won't boot without it) |
| `DJANGO_ALLOWED_HOSTS` | Host header allowlist | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | web origins | `localhost:8081,localhost:19006` |
| `CSRF_TRUSTED_ORIGINS` | prod CSRF origins | unset (comma-separated; used at `DEBUG=False`) |
| `SECURE_HSTS_SECONDS` | HSTS max-age | `31536000` (1 yr) when `DEBUG=False` |
| `REDIS_URL` | Celery broker/result | `redis://localhost:6379/5` |
| `CELERY_TASK_ALWAYS_EAGER` | run tasks inline | `true` (dev/test) |
| `SUPABASE_URL` | Supabase project URL (JWKS derives from it) | **required** (auth verifies nothing without it; boot-blocked in prod) |
| `SUPABASE_JWT_SECRET` | legacy HS256 fallback verification | set from dashboard (unused on ES256 projects) |
| `SUPABASE_SERVICE_ROLE_KEY` | Admin API (advisor invites) | set from dashboard; server-only |
| `EMAIL_HOST` + `EMAIL_*` | Django's own mail (reminders, alerts) via SMTP | unset → console backend; **required** when `DEBUG=False` (boot-blocked) |
| `SENTRY_DSN` | error tracking | unset (Sentry activates only in prod) |

> Supabase **Auth** mail (signup confirmation / OTP codes) is configured in the
> Supabase dashboard (custom SMTP → Resend), not here — both mail paths point at
> the same provider.

### Mobile (`app.config.js`, loaded from `mobile/.env`)
| Var | Purpose | Dev default |
|---|---|---|
| `WAYFARA_API_URL` | backend base URL baked into `extra.apiUrl` | `http://localhost:8010` |
| `SUPABASE_URL` | Supabase project URL | required for auth |
| `SUPABASE_ANON_KEY` | publishable client key (safe to ship) | required for auth |
| `REACT_NATIVE_PACKAGER_HOSTNAME` | pin Metro to a specific LAN IP | auto |

### Local dev notes
- **Backend port.** The dev machine's :8000 is taken by an unrelated system, so
  Wayfara's Django dev server runs on **:8010** and `WAYFARA_API_URL` points
  there.
- **OTP in dev.** Codes are real email now (Supabase → Resend). Until a sending
  domain is verified in Resend, delivery only works to the Resend account's own
  address — sign up test accounts with that email. Django's console backend only
  covers Django's *own* mail (reminders), which just prints to the server log.
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
| 1 | Frontend foundations | 🟢 | Nav, Supabase-backed auth state, typed API client, onboarding spine, design system |
| 2 | APIs & backend logic | 🟢 | 7 apps; matching + timeline engines; advisor; scraper; versioned `/api/v1/`; strict input validation on every serializer |
| 3 | Database & storage | 🟢 | Postgres :5433 + migrations done; documents on **Cloudflare R2** (private bucket, signed URLs, live-verified July 2026); advisor audio still local (minor) |
| 4 | Auth & permissions | 🟢 | Supabase identity (password + OTP fallback, ES256/JWKS-verified); roles; row-level scoping |
| 5 | Hosting & deployment | 🔴 | Not started (Railway planned; env-driven config already prepped); `/healthz` ready for the platform health check |
| 6 | Cloud & compute | 🟡 | Celery/Redis/Beat designed & correct; runs only locally |
| 7 | CI/CD & version control | 🟡 | GitHub Actions CI (Postgres service) + guardrail tests for API versioning/strict-serializer conventions; **no CD** (blocked on Layer 5) |
| 8 | Security & RLS | 🟢 | App-layer scoping; credentials offloaded to Supabase; SECRET_KEY/SUPABASE_URL/SMTP fail-fasts; `SECURE_*`/HSTS/cookie flags wired (auto-on at `DEBUG=False`) |
| 9 | Rate limiting | 🟢 | DRF global + onboarding throttles; auth-endpoint limits are Supabase's |
| 10 | Caching & CDN | 🟡 | Redis cache + cached discovery API; **CDN untouched** (no static/media host yet) |
| 11 | Load balancing & scaling | 🔴 | Stateless design honoured; nothing to balance yet (blocked on Layer 5); `/healthz` ready as the LB health-check target |
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

1. **~~Media on local disk (Layer 3)~~ — code-side DONE (July 2026).**
   Document storage now runs on **Cloudflare R2** (django-storages, private
   bucket, 10-min signed URLs, authorize-then-serve) with a local-disk dev
   fallback; production **refuses to boot** without R2 keys. Bucket + keys
   live and verified (July 2026: upload → bucket, signed GET 200, tampered/
   unsigned 400). Remaining: moving advisor audio to the same storage path.
2. **Production API URL is deploy-time.** `app.config.js` defaults `apiUrl` to
   `localhost:8010`. A shipped build **must** get `WAYFARA_API_URL` set to the
   real HTTPS host or every API call fails on-device — this is about the
   `localhost`, not the port.
3. **NativeWind v5 is preview software.** Works today; fallback is pinning a
   known-good nightly. Also the reason SDK 57 may outrun public Expo Go.
4. **~~`grades` isn't yet a matching signal~~ — DONE (July 2026).** Awais's
   product decision: grades add a flat per-student boost to every program's
   score — **exceptional** (GPA ≥3.5 / marks ≥95% / A*) +25, **strong**
   (≥3.0 / ≥85% / A) +15, **good** (≥2.5 / ≥75% / B) +8, weak/missing +0
   (encourage, don't punish a data gap). An exceptional profile with solid
   language headroom reaches **100** on a well-fitting program. See 4.3;
   tested in `applications/tests.py::AcademicStrengthScoringTests`.
5. **Field-of-study taxonomy is hardcoded in the app.** The onboarding form's
   field chips (IT/Business/Design/Engineering) must match the Opintopolku
   catalogue's values; a `/api/v1/fields/` endpoint would remove the duplication.
6. **Migri figures are stubbed / snapshotted.** The scraper's Migri source is a
   stub; `Visa.funds_required_eur` and `PolicyFigure` are snapshots that need
   verification against Migri's current numbers before Phase 4 content ships.
7. **Payment layer not built.** `User.tier` is webhook-driven by design, but the
   `Payment` model + gateway integration land later (with merchant onboarding).
8. **~~Auth hardening follow-ups (July 2026 scan)~~ — SUPERSEDED.** All three
   were closed, then the whole home-grown auth layer was replaced by Supabase
   (3.4) — credentials/OTP storage are no longer Django's problem at all. The
   deploy-time action is setting the prod env vars in §6 (the fail-fasts
   enforce them).
9. **Auth email delivery is dev-scoped.** Resend has no verified sending
   domain yet, so Supabase's codes only deliver to the Resend account's own
   inbox. **Verifying a domain (SPF/DKIM) is a launch prerequisite** — without
   it no real user can sign up. Same domain then feeds Django's `EMAIL_*`.

---

## 9. Roadmap & open items

Near-term, roughly ordered:

1. **Layer 1 breadth** — Apps/Chat tabs (Profile + Explore/matches already
   shipped, with deliberate sign-out behind a confirm) and the
   advisor/messaging surface. (Push registration + notification inbox
   shipped July 2026 with the notification platform.)
2. **Layer 3 storage** — S3/R2 + signed access, before document upload UI.
3. **Hosting (Layer 5, when ready)** — Railway: set the env vars above, get TLS +
   the `SECURE_*` settings, wire CD, point uptime monitoring. Unblocks ~5 layers.
4. **Payments (Week 9)** — `Payment` model, Pakistani gateway webhook → `tier`.
5. **AI layer** — "Ask Wayfara" over `chat`, document AI review (Premium), and the
   free [AI match showcase](#39-free-ai-match-showcase-planned).
6. **Data pipeline hardening** — real Migri selectors; verify snapshot figures.

Open questions to revisit: migrations vs first deploy target; NativeWind v5
stable; Pakistani gateway merchant onboarding (needs business docs); a
`/api/v1/fields/` endpoint for the onboarding taxonomy.
