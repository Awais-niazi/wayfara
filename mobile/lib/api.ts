/**
 * Typed API client for the Wayfara Django backend.
 *
 * Auth model: passwordless OTP. The Get Started form (`onboarding`) creates
 * the account and emails a 6-digit code; `verifyOtp` exchanges email + code
 * for JWT tokens (it is also the login). Tokens rotate on refresh — the
 * refresh endpoint returns BOTH a new access and a new refresh token.
 *
 * The client is transport-only: token persistence and refresh-on-401 live in
 * `context/AuthContext.tsx`, which registers itself via `configureApi`.
 */
import Constants from "expo-constants";
import { Platform } from "react-native";

function defaultApiUrl(): string {
  const configured = Constants.expoConfig?.extra?.apiUrl as string | undefined;
  if (configured) return configured;
  // Android emulators reach the host machine at 10.0.2.2, not localhost.
  if (Platform.OS === "android") return "http://10.0.2.2:8000";
  return "http://localhost:8000";
}

export const API_URL = defaultApiUrl();

// ─── Wire types (mirror the DRF serializers) ────────────────────────────────

export interface Tokens {
  access: string;
  refresh: string;
}

export interface Me {
  email: string;
  role: "student" | "advisor" | string;
  tier: "free" | "full" | "premium" | string;
  email_verified: boolean;
  /** False until onboarding step 3 (create password) is done. */
  has_password: boolean;
  onboarding_complete: boolean;
}

export type StudyLevel = "undergraduate" | "masters";
export type LanguageTestStatus = "not_taken" | "booked" | "taken";
export type LanguageTest = "ielts" | "toefl" | "pte" | "duolingo";
export type GradeScale = "gpa_4" | "percentage" | "letter";
export type Intake = "september" | "january";
export type Stage = "exploring" | "ready" | "applied";

export interface OnboardingForm {
  email: string;
  study_level: StudyLevel;
  field_of_study: string;
  grade_scale?: GradeScale;
  grades?: string;
  language_test_status?: LanguageTestStatus;
  language_test?: LanguageTest;
  language_test_score?: string;
  budget_eur_per_year?: number;
  intake?: Intake;
  intake_year?: number;
  stage?: Stage;
}

export interface Profile {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  tier: string;
  nationality: string;
  phone: string;
  home_city: string;
  study_level: StudyLevel | "";
  field_of_study: string;
  grade_scale: GradeScale | "";
  grades: string;
  language_test_status: LanguageTestStatus | "";
  language_test: LanguageTest | "";
  language_test_score: string;
  budget_eur_per_year: number | null;
  intake: Intake | "";
  intake_year: number | null;
  stage: Stage | "";
  current_phase: number;
  onboarding_completed: boolean;
}

export interface Match {
  id: number;
  program: number;
  program_name: string;
  degree_level: string;
  university: string;
  university_id: number;
  city: string;
  campus: string | null;
  tuition_fee_eur: string | null; // DRF DecimalField serializes as string
  duration_years: string | null;
  application_deadline: string | null; // ISO date
  world_ranking: number | null;
  featured: boolean;
  data_verified: boolean;
  fit: "safety" | "good_fit" | "reach";
  score: string; // 0–100, decimal string
  created_at: string;
}

export interface CatalogProgram {
  id: number;
  name: string;
  degree_level: string;
  field_of_study: string;
  language: string;
  duration_years: string | null;
  tuition_fee_eur: string | null;
  scholarship_available: boolean;
  intake: string;
  application_deadline: string | null; // ISO date
  min_ielts_score: string | null;
  campus: string | null;
}

export interface UniversityDetail {
  id: number;
  name: string;
  institution_type: string;
  city: string;
  logo_url: string;
  website: string;
  description: string;
  world_ranking: number | null;
  ranking_system: string;
  ranking_year: number | null;
  featured: boolean;
  data_verified: boolean;
  /** Curated editorial overview; empty until human-reviewed. */
  overview: string;
  programs: CatalogProgram[];
}

export type TaskStatus = "pending" | "completed" | "skipped";

export interface Task {
  id: number;
  phase: number;
  title: string;
  description: string;
  due_date: string | null; // ISO date
  order: number;
  status: TaskStatus;
  is_critical: boolean;
  completed_at: string | null;
}

// ─── Error type ──────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `API error ${status}`,
    );
    this.status = status;
    this.body = body;
  }
}

/** Human-readable message from an API failure — surfaces the first DRF
 *  validation error ({ field: ["msg"] }), with a friendly network fallback. */
export function firstErrorMessage(err: unknown): string {
  if (err instanceof ApiError && typeof err.body === "object" && err.body !== null) {
    for (const [field, msgs] of Object.entries(err.body as Record<string, unknown>)) {
      const msg = Array.isArray(msgs) ? msgs[0] : msgs;
      if (typeof msg === "string") {
        return field === "detail" || field === "non_field_errors" ? msg : `${field}: ${msg}`;
      }
    }
  }
  if (err instanceof Error && err.message === "Network request failed") {
    return "Can't reach the server. Is the backend running?";
  }
  return err instanceof Error ? err.message : "Something went wrong.";
}

// ─── Core request machinery ──────────────────────────────────────────────────

interface ApiHooks {
  /** Returns the current access token, or null when signed out. */
  getAccessToken: () => string | null;
  /** Called on a 401 from an authed request; should refresh and return the
   *  new access token, or null if the session is unrecoverable. */
  onUnauthorized: () => Promise<string | null>;
}

let hooks: ApiHooks = {
  getAccessToken: () => null,
  onUnauthorized: async () => null,
};

/** AuthContext registers its token accessors here at mount. */
export function configureApi(next: ApiHooks) {
  hooks = next;
}

// Every endpoint below lives under this one versioned prefix on the backend
// (wayfara/urls.py); call sites pass just the resource path (e.g. "/me/"),
// never "/api/...", so a version bump is a one-line change here.
const API_VERSION_PREFIX = "/api/v1";

async function request<T>(
  path: string,
  init: RequestInit = {},
  { auth = true, retried = false }: { auth?: boolean; retried?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (auth) {
    const token = hooks.getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${API_VERSION_PREFIX}${path}`, { ...init, headers });

  if (res.status === 401 && auth && !retried) {
    const fresh = await hooks.onUnauthorized();
    if (fresh) return request<T>(path, init, { auth, retried: true });
  }

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(res.status, body);
  }

  if (res.status === 204 || res.status === 205) return undefined as T;
  return (await res.json()) as T;
}

const post = (body: unknown): RequestInit => ({
  method: "POST",
  body: JSON.stringify(body),
});

// ─── Endpoints ───────────────────────────────────────────────────────────────

/** The Get Started form (anonymous). Creates the account + emails the OTP. */
export function submitOnboarding(form: OnboardingForm) {
  return request<{ detail: string; email: string }>("/onboarding/", post(form), {
    auth: false,
  });
}

/** Send a login code to an existing account. Always 200 (no enumeration). */
export function requestOtp(email: string) {
  return request<{ detail: string }>("/auth/otp/request/", post({ email }), {
    auth: false,
  });
}

/** Exchange email + 6-digit code for JWT tokens. This IS the login. */
export function verifyOtp(email: string, code: string) {
  return request<Tokens>("/auth/otp/verify/", post({ email, code }), {
    auth: false,
  });
}

/** Password login for returning users who set one (onboarding step 3). */
export function loginWithPassword(email: string, password: string) {
  return request<Tokens>("/auth/token/", post({ email, password }), {
    auth: false,
  });
}

/** Rotate the refresh token; returns a new access AND refresh pair. */
export function refreshTokens(refresh: string) {
  return request<Tokens>("/auth/token/refresh/", post({ refresh }), {
    auth: false,
  });
}

/** Session bootstrap — 401 means signed out. */
export function getMe() {
  return request<Me>("/me/");
}

/** Onboarding step 3: create the account password (authenticated). */
export function setPassword(password: string) {
  return request<{ detail: string }>("/auth/password/", post({ password }));
}

/** Blacklist the refresh token server-side. */
export function logout(refresh: string) {
  return request<void>("/auth/logout/", post({ refresh }));
}

export function getProfile() {
  return request<Profile>("/profile/");
}

export function updateProfile(patch: Partial<Profile>) {
  return request<Profile>("/profile/", {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

/** University recommendations, best fit first. */
export function getMatches() {
  return request<Match[]>("/matches/");
}

/** AI-curated highlight: at most 2-3 matches the AI layer singled out, each
 *  with a one-line reason. The endpoint is the free AI-layer task — until it
 *  ships, this 404s and Home hides the showcase box. */
export interface AiMatch extends Match {
  /** Why the AI picked this university for this student. */
  reason?: string;
}

export function getAiMatches() {
  return request<AiMatch[]>("/matches/ai/");
}

/** One university with curated KB fields + its active programmes (public, cached). */
export function getUniversity(id: number) {
  return request<UniversityDetail>(`/universities/${id}/`, {}, { auth: false });
}

/** The journey plan; optionally scoped to one phase. */
export function getTasks(phase?: number) {
  const qs = phase !== undefined ? `?phase=${phase}` : "";
  return request<Task[]>(`/tasks/${qs}`);
}

export function setTaskStatus(id: number, status: TaskStatus) {
  return request<Task>(`/tasks/${id}/status/`, post({ status }));
}
