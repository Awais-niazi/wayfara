# Wayfara Support Playbook

Written by the app's first support engineer, from incidents that actually
happened (July 2026 testing weeks). When something looks broken: find the
symptom in §7, follow LOOK → CAUSES → FIX → VERIFY. When an alert fires, its
message names its entry here.

**Rule zero: nothing on this machine touches port 5432.** That is Ash's
read-only Helsinki replica — not Wayfara's. Never promote it, never write to
it, never "fix" it. Wayfara's Postgres is the cluster on **5433** (db
`wayfara`).

---

## 1. First 15 minutes of any incident

1. **Scope it** — one student or everyone? One screen or the whole app?
2. `curl -s localhost:8010/healthz` — process + DB up?
3. `curl -s localhost:8010/healthz/deep | python3 -m json.tool` — which
   dependency or heartbeat is red? (§5 explains every field.)
4. **Sentry** → filter `environment:production` — is an exception spiking?
   Check Releases to see if it started with a deploy.
5. **Heartbeats** — admin → Ops → Heartbeats: did a periodic job go quiet?
   (`last_ok` old, or `last_error` fresh.)
6. If a deploy caused it: roll back first, diagnose second.
7. Find the symptom in §7 and follow the entry.

## 2. Severity ladder

| Sev | Meaning | Response |
|-----|---------|----------|
| S1 | Login, onboarding, or the API down for everyone | Drop everything. Rollback > diagnosis. |
| S2 | A core flow broken (matching, documents, notifications) but app up | Same day. |
| S3 | Degraded: pushes late, one canary firing, one screen glitched | Within a couple of days. |
| S4 | Cosmetic / data-quality (one bad programme row, copy bug) | Backlog. |

## 3. System map

| Piece | Where | Notes |
|---|---|---|
| Django API | dev `localhost:8010` (Ash holds 8000) | everything under `/api/v1/`; `/healthz`, `/healthz/deep`, `/admin/` outside it |
| Expo app | dev `localhost:8081` (Metro) | web + iOS + Android from one codebase |
| Postgres | **5433**, db `wayfara` | 5432 is Ash's replica — DO NOT TOUCH |
| Redis | localhost:6379 **db 5** broker, **db 6** cache | keyspace split keeps Ash's Redis usage untouched |
| Celery | worker + beat (DB scheduler) | dev runs eager (no worker needed); prod runs both processes |
| Supabase (Singapore) | auth.wayfara project | owns identity; Django verifies JWTs via JWKS (ES256) |
| Cloudflare R2 | bucket `wayfara-documents`, private | signed URLs, 600 s expiry |
| Resend | SMTP for Supabase auth mail + Django mail | **sandbox until domain verified** — only delivers to the account owner's address (launch blocker) |
| Expo push | exp.host API | tickets checked at send, receipts checked by ops task |
| Sentry | backend + mobile projects | alerts → Discord `#alerts` → phone push |

## 4. Config inventory

Backend env lives in `backend/.env` (gitignored) in dev; Railway variables in
prod. Every value marked **fail-fast** refuses to boot production when
missing — a crash at deploy is intentional and better than silent breakage.

### Backend

| Variable | What it does | Wrong/missing → symptom |
|---|---|---|
| `DJANGO_SECRET_KEY` | session/CSRF signing | **fail-fast** in prod |
| `DJANGO_DEBUG` | never `true` in prod | debug pages leak config |
| `DJANGO_ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` | host allow-list | 400 Bad Request on every call / CSRF failures in admin |
| `DATABASE_URL` | Postgres DSN (dev: port **5433**) | falls back to sqlite — data "disappears" |
| `REDIS_URL` | Celery broker (db 5) | tasks queue nowhere; worker idle |
| `CACHE_URL` | cache + throttle counters (db 6) | throttles reset per worker |
| `CELERY_TASK_ALWAYS_EAGER` | `true` dev (inline tasks), `false` prod | prod `true` = tasks block requests; dev `false` without a worker = nothing background ever runs |
| `SUPABASE_URL` | JWKS verification + admin API | **fail-fast**; wrong → every request 401 |
| `SUPABASE_JWT_SECRET` | legacy HS256 fallback only | ES256 projects don't need it; harmless if stale |
| `SUPABASE_SERVICE_ROLE_KEY` | admin API (advisor provisioning, user wipes) | admin ops fail; NEVER ships client-side |
| `R2_ACCOUNT_ID` `R2_ACCESS_KEY_ID` `R2_SECRET_ACCESS_KEY` `R2_BUCKET` | document storage | **fail-fast** in prod. Account ID is **32 hex chars** — a mistyped 33-char ID presents as `SSLV3_ALERT_HANDSHAKE_FAILURE` (§7.6) |
| `EMAIL_HOST` `EMAIL_HOST_USER` `EMAIL_HOST_PASSWORD` `EMAIL_PORT` `EMAIL_USE_TLS` | Django SMTP (Resend) | **fail-fast** in prod (console backend drops mail) |
| `DEFAULT_FROM_EMAIL` / `SCRAPER_ALERT_EMAIL` | sender / critical-change review alerts | scraper review emails go nowhere |
| `PUSH_ENABLED` | hard kill-switch for Expo push | `false` = no pushes at all (check FIRST when "pushes stopped") |
| `SENTRY_DSN` / `SENTRY_ENVIRONMENT` / `SENTRY_RELEASE` / `SENTRY_TRACES_SAMPLE_RATE` | error tracking | dev must set `SENTRY_ENVIRONMENT=development` or dev noise pollutes prod alerts |
| `SECURE_HSTS_SECONDS` / `LOG_LEVEL` / `CELERY_TIMEZONE` / `ADVISOR_CONSOLE_URL` | transport sec / log verbosity / scraper clock (Helsinki) / console links | low-risk knobs |

### Mobile (`mobile/.env`, gitignored → `app.config.js` → `Constants.expoConfig.extra`)

| Variable | What it does | Wrong/missing → symptom |
|---|---|---|
| `WAYFARA_API_URL` | backend base URL (dev default `http://localhost:8010`) | every screen shows "couldn't load" |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | client auth (anon key is safe to ship) | signup/login button errors "Supabase isn't configured" |
| `SENTRY_DSN_MOBILE` | client crash reporting (DSN is public-safe) | unset = Sentry off (silent, by design) |

**Env changes need restarts**: backend picks up `.env` on server restart;
mobile needs Metro restarted **with `--clear`** (§7.11).

### Scheduled jobs & idempotent setup commands (run all on every deploy)

| Command | Creates |
|---|---|
| `manage.py setup_notification_schedule` | reminder dispatcher, every 5 min |
| `manage.py setup_scraper_schedule` | monthly scrape, 1st @ 02:00 Helsinki |
| `manage.py setup_ops_schedule` | beat-pulse 5 min · push-receipts 15 min · canaries 60 min |
| `manage.py seed_task_templates` | journey timeline templates |
| `manage.py seed_university_websites` | official uni sites (never overwrites) |
| `manage.py backfill_studyinfo_oids` | Studyinfo deep links + twin merges (run after each scraper run) |

## 5. Monitoring surfaces

**Three layers.** Exceptions → Sentry. Liveness → heartbeats. Correctness →
canaries. A silent failure has to slip through all three.

- **`/healthz`** — cheap liveness (process + DB). Uptime pinger target #1.
- **`/healthz/deep`** — exercises DB, Redis broker, R2, Supabase JWKS, and
  every heartbeat's staleness; 503 when anything is wrong. Uptime pinger
  target #2. In dev (eager mode) broker/heartbeats report
  `skipped (eager mode)` — that is normal, not a failure.
- **Heartbeats** (admin → Ops) — dead-man switches with budgets:
  `celery-beat` 15 min · `reminder-dispatcher` 20 min · `push-receipts` 1 h ·
  `canaries` 3 h · `scraper-monthly` 35 d. `last_result` stores the last run's
  counters — useful history even when healthy.
- **Canaries** (hourly, findings → Sentry → Discord):

| Canary | Fires when | First move |
|---|---|---|
| ZERO matches | onboarded ≥30 min, budget>0, no matches | §7.3 |
| never pushed | notification ≥15 min old, user has devices, no push stamp | §7.4 |
| missing blob | recent Document with no object in storage | §7.6 |
| INACTIVE programmes | matches pointing at deactivated rows | §7.8 |
| heartbeats stale | sibling job quiet while worker alive (prod only) | §7.5 |

- **Sentry → Discord**: all alert rules post to `#alerts`; the Discord app
  delivers the phone push (Sentry has no mobile app). This path works even
  when our backend is completely down.

## 6. Alert response quick table

| Alert | Meaning | Entry |
|---|---|---|
| Uptime: `/healthz` down | API down or host dead | §7.1 |
| Uptime: `/healthz/deep` 503 | a dependency or heartbeat is red — read `checks` | §7.5 / §7.6 |
| Sentry exception spike | code path broken (check release) | §1 step 4 |
| Canary message | product broken without an exception | table in §5 |
| `Expo push receipt error` | pushes accepted but not delivered | §7.4 |

## 7. Incident catalog

### 7.1 API down / every request failing
**LOOK** `curl -sv localhost:8010/healthz` · server log · Railway status.
**CAUSES** process crashed at boot (a fail-fast fired — read the
`ImproperlyConfigured` message, it names the missing variable) · DB down ·
bad deploy.
**FIX** missing config → set it, restart. Bad deploy → roll back. DB →
`pg_isready -p 5433`; **never** touch 5432.
**VERIFY** `/healthz` 200, `/healthz/deep` all ok.

### 7.2 Student gets no OTP / confirmation email  *(real incident, 17 Jul 2026)*
**LOOK** Supabase dashboard → Auth → Users: did the attempt create a user?
Resend dashboard → deliveries.
**CAUSES** in observed order:
1. **Email already registered + confirmed** — Supabase anti-enumeration
   returns fake success with an *empty `identities` array* and sends nothing.
   The wizard detects this and says "already registered" (GetStartedScreen);
   if that regressed, this is the first suspect.
2. **Resend sandbox** — until the domain is verified, mail delivers ONLY to
   the Resend account owner's address. Launch blocker; test with that inbox.
3. Supabase email rate limits (dashboard → Auth → Rate limits).
4. SMTP creds changed/expired in Supabase dashboard → Auth → SMTP.
**FIX** (1) student logs in instead — email-code path if password forgotten.
(2) verify domain / use the owner inbox. To re-test a used address, wipe the
test user on BOTH sides (§8).
**VERIFY** fresh signup with a deliverable address receives a 6-digit code.

### 7.3 Student sees no matches  *(real incident, 17 Jul 2026)*
**LOOK** `manage.py shell` →
`from applications.services import match_programs_for_student;
match_programs_for_student(<student_id>)` — returns the count and surfaces
exceptions. Walk the filter chain: active → deadline not passed → degree
level → field `icontains` → budget.
**CAUSES**
1. **Blank budget** = "tuition-free only" **by design** — and tuition-free
   non-EU programmes are near-nonexistent. The app now says so with a
   "set a budget" CTA; if a student writes in confused, this is it.
2. Matching task never ran — dev: server started with `CELERY_TASK_ALWAYS_EAGER=false`
   and no worker; prod: worker down (heartbeats stale too).
3. All deadlines in the catalog passed (post-round lull) — legitimate.
**FIX** (1) student sets a budget — profile edits re-match instantly
(`MATCH_RELEVANT_FIELDS`). (2) fix worker/eager, run the shell call above.
**VERIFY** `/api/v1/matches/` non-empty; card carries a sane % score.

### 7.4 Push notifications not arriving
**LOOK** `PUSH_ENABLED`? → user's DeviceTokens (admin) → Notification rows
(`push_sent_at` stamped?) → Heartbeats `push-receipts` `last_result`
(delivered vs pruned vs errors) → Sentry `push-receipt-error`.
**CAUSES** kill-switch off · no device token (web-only user — expected; or
registration failed) · **Android Expo Go cannot receive remote push since
SDK 53 — dev build required** (not a bug) · token pruned after uninstall ·
Expo outage (receipt errors).
**FIX** per cause; inbox (bell) always has the durable copy regardless.
**VERIFY** send yourself a Broadcast (admin → Notifications → Broadcasts →
send now) → push arrives; receipts task reports `delivered ≥ 1`.

### 7.5 Background jobs went quiet (reminders late, scraper skipped)
**LOOK** `/healthz/deep` → `heartbeats` block; admin → Ops → Heartbeats.
`celery-beat` stale = beat or ALL workers down. One job stale while
`celery-beat` fresh = that job is failing — read its `last_error_message`.
**CAUSES** beat/worker process dead (OOM, deploy forgot to start them) ·
Redis down (`broker` check red) · schedule rows missing (setup commands not
run on a fresh DB).
**FIX** restart worker+beat · re-run the three `setup_*_schedule` commands ·
Redis first if broker is red.
**VERIFY** pulses fresh within 5–10 min. Missed reminders older than 24 h are
**deliberately swallowed** (STALE_AFTER) — students must not get a week of
stale pings; don't "fix" that.

### 7.6 Document upload / download failures  *(R2)*
**LOOK** `/healthz/deep` `storage` · Sentry · try a signed URL by hand (§8).
**CAUSES** `SSLV3_ALERT_HANDSHAKE_FAILURE` = **R2 account ID typo'd (must be
32 hex chars)** — seen live, cost an hour · rotated/dead token → 403 ·
signed URL past its 600 s expiry or tampered → 400 (correct behavior!) ·
missing-blob canary = rows whose object vanished (upload raced a failure, or
out-of-band deletion).
**FIX** creds in `backend/.env` / Railway; restart. Missing blobs: student
re-uploads (checklist shows the slot unfilled).
**VERIFY** upload in app → object visible in Cloudflare dash → View opens it.

### 7.7 Everyone gets 401s / login loops
**LOOK** Sentry auth errors · decode a failing JWT's header (`alg`, `kid`) ·
Supabase dashboard → JWT keys.
**CAUSES** Supabase signing key rotated (JWKS cache holds ~1 h) ·
`SUPABASE_URL` wrong → JWKS unreachable (deep health `supabase` red) ·
clock skew on host.
**FIX** restart backend (drops JWKS cache) · fix URL · sync clock.
**VERIFY** fresh login → `/api/v1/me/` 200.

### 7.8 Catalog duplicates / bad programme data
**LOOK** two near-identical programmes at one university, one with
`external_id`, one without → scraper twin (it upserts by oid and can't
converge into hand-seeded rows).
**FIX** `manage.py backfill_studyinfo_oids` (dry-run first) — merges twins
into curated rows, re-matches affected students; ambiguous rows are listed
for manual `external_id` entry in admin. Critical field changes from scrapes
always wait in admin → Scraping → Data changes for review.
**VERIFY** the INACTIVE-programmes canary stays quiet; gate buttons deep-link.

### 7.9 Studyinfo link lands somewhere useless  *(real incident, 17 Jul 2026)*
**LOOK** does the Program have `external_id`? Is the programme even published
on Studyinfo (`konfo-backend/search/koulutukset?keyword=...`)?
**CAUSES** no oid → search fallback (run 7.8's backfill) · **programme's
round not yet published by Studyinfo** — no URL exists anywhere; the GATE
card's university-site link is the correct answer · seasons: most of the
year NO application form is live anywhere (main round January; autumn round
31 Aug–10 Sep). The gate banner states this; it is not a bug.
**REMEMBER** apply-in-January = September start; January start = apply
31 Aug–10 Sep. Universities have no portals of their own — Studyinfo is the
only gate.

### 7.10 Payments/tier issues
Payments run on the **website** with Pakistani gateways (Easypaisa/JazzCash/
cards) — never Stripe/IAP in-app. Tier unlocks via the account server-side.
Not built yet; entry reserved.

### 7.11 App shows stale UI / new feature "missing"
**LOOK** is it web? Did Metro restart after a dependency change?
**FIX** browser hard-refresh (Ctrl+Shift+R) · `npx expo start --clear` after
any new package or env change · check `WAYFARA_API_URL` points at :8010.
**Note** RN-web `Alert.alert` is a NO-OP — web confirms must use
`window.confirm` (helpers exist; grep before adding any new Alert).

### 7.12 Database emergencies
Backup before surgery: `pg_dump -p 5433 wayfara > backup_$(date +%F).sql`.
Migration conflicts: never edit an applied migration; add a new one.
FK errors mentioning a dropped app's tables (seen with `token_blacklist_*`):
orphaned tables — drop them AND their `django_migrations` rows.
**And once more: 5432 is Ash's. Do not touch it.**

## 8. Ops crib sheet

```bash
# health
curl -s localhost:8010/healthz/deep | python3 -m json.tool

# run any ops job by hand (dev, eager)
.venv/bin/python manage.py shell -c "from ops.services import run_canaries; print(run_canaries())"
.venv/bin/python manage.py shell -c "from ops.services import check_push_receipts; print(check_push_receipts())"
.venv/bin/python manage.py shell -c "from notifications.services import dispatch_due_reminders; print(dispatch_due_reminders())"

# re-match one student / regenerate their timeline
.venv/bin/python manage.py shell -c "from applications.services import match_programs_for_student; print(match_programs_for_student(ID))"

# wipe a TEST user on both sides (Supabase + Django) — needed to reuse an email
# NOTE: bash reserves $UID — use another variable name (cost us a real hour)
set -a; source backend/.env; set +a
SB_UID=$(curl -s "$SUPABASE_URL/auth/v1/admin/users?per_page=20" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  | python3 -c "import json,sys; print(next((u['id'] for u in json.load(sys.stdin)['users'] if u['email']=='EMAIL'),''))")
curl -s -X DELETE "$SUPABASE_URL/auth/v1/admin/users/$SB_UID" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
.venv/bin/python manage.py shell -c "
from accounts.models import User
from students.models import Document
u = User.objects.get(email='EMAIL')
for d in Document.objects.filter(student__user=u):
    if d.file: d.file.delete(save=False)
u.delete()"

# Studyinfo deep links after a scraper run
.venv/bin/python manage.py backfill_studyinfo_oids --dry-run   # then without

# force a Sentry test event (verifies the whole alert path to Discord)
.venv/bin/python manage.py shell -c "import sentry_sdk; sentry_sdk.capture_message('Wayfara alert-path test', level='error')"
```

## 9. Deploy-day arming checklist (Railway)

- [ ] All backend env vars set (§4) — the fail-fasts will name anything missed
- [ ] `SENTRY_ENVIRONMENT=production`, `CELERY_TASK_ALWAYS_EAGER=false`, `DJANGO_DEBUG=false`
- [ ] Three processes: web, `celery -A wayfara worker`, `celery -A wayfara beat --scheduler django_celery_beat.schedulers:DatabaseScheduler`
- [ ] Run: `migrate` + all six setup/seed commands (§4)
- [ ] Uptime monitor (UptimeRobot/Better Stack): `/healthz` every 1 min AND `/healthz/deep` every 5 min, alert on non-200 → email + their phone app
- [ ] Sentry: alert rules → Discord `#alerts` verified with the §8 test event
- [ ] Mobile: `WAYFARA_API_URL` → Railway URL, `SENTRY_DSN_MOBILE` set in EAS
- [ ] Resend domain verified (until then auth mail reaches ONLY the owner inbox)
- [ ] Rotate the R2 token that appeared in a screenshot during setup (July 2026)

## 10. After every incident

Three lines, appended to this file's incident catalog (new entry or a note on
an existing one): what broke · how we knew · what fixed it. The July 2026
entries exist because the pattern works — every incident makes this playbook
smarter, and this playbook is the institutional memory of a one-person team.
