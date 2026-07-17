/**
 * Typed API client for the Wayfara Django backend.
 *
 * Auth model: Supabase owns identity. The app authenticates against Supabase
 * (see lib/supabase.ts); this client reads the current Supabase access token
 * per request and forwards it as a Bearer credential. On a 401 it asks
 * Supabase to refresh the session once, then retries.
 */
import Constants from "expo-constants";
import { Platform } from "react-native";

import { supabase } from "./supabase";

function defaultApiUrl(): string {
  const configured = Constants.expoConfig?.extra?.apiUrl as string | undefined;
  if (configured) return configured;
  // Android emulators reach the host machine at 10.0.2.2, not localhost.
  if (Platform.OS === "android") return "http://10.0.2.2:8000";
  return "http://localhost:8000";
}

export const API_URL = defaultApiUrl();

// ─── Wire types (mirror the DRF serializers) ────────────────────────────────

export interface Me {
  email: string;
  first_name: string;
  role: "student" | "advisor" | string;
  tier: "free" | "full" | "premium" | string;
  email_verified: boolean;
  onboarding_complete: boolean;
}

export type StudyLevel = "undergraduate" | "masters";
export type LanguageTestStatus = "not_taken" | "booked" | "taken";
export type LanguageTest = "ielts" | "toefl" | "pte" | "duolingo";
export type GradeScale = "gpa_4" | "percentage" | "letter";
export type Intake = "september" | "january";
export type Stage = "exploring" | "ready" | "applied";

export interface OnboardingForm {
  first_name: string;
  last_name: string;
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
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${API_VERSION_PREFIX}${path}`, { ...init, headers });

  if (res.status === 401 && auth && !retried) {
    // Token may have lapsed between refreshes — ask Supabase for a fresh one.
    const { data } = await supabase.auth.refreshSession();
    if (data.session) return request<T>(path, init, { auth, retried: true });
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

/** The Get Started form. The user is already Supabase-authenticated; this
 *  records their name, stores the profile, and kicks off matching. */
export function submitOnboarding(form: OnboardingForm) {
  return request<{ detail: string; first_name: string }>("/onboarding/", post(form));
}

/** Session bootstrap — 401 means signed out. */
export function getMe() {
  return request<Me>("/me/");
}

/** Best-effort server cleanup on sign-out: drop this device's push token.
 *  Session revocation itself is Supabase's `signOut()` (client-side). */
export function logout(deviceToken?: string) {
  return request<void>("/auth/logout/", post(deviceToken ? { device_token: deviceToken } : {}));
}

// ─── Applications (the workspace) ────────────────────────────────────────────

export type ApplicationStatus =
  | "shortlisted"
  | "in_progress"
  | "submitted"
  | "offer_received"
  | "waitlisted"
  | "rejected"
  | "place_confirmed"
  | "withdrawn";

export type DocType =
  | "passport"
  | "photo"
  | "transcript"
  | "degree_certificate"
  | "language_certificate"
  | "bank_statement"
  | "sponsor_letter"
  | "health_insurance"
  | "acceptance_letter"
  | "tuition_receipt"
  | "accommodation_proof"
  | "cv"
  | "motivation_letter"
  | "recommendation_letter"
  | "other";

export interface ChecklistItem {
  doc_type: DocType;
  label: string;
  required: boolean;
  notes: string;
  fulfilled: boolean;
  document_id: number | null;
}

export interface Application {
  id: number;
  status: ApplicationStatus;
  fit: "safety" | "good_fit" | "reach" | "";
  priority: number;
  program: number;
  program_name: string;
  university: string;
  university_id: number;
  city: string;
  degree_level: string;
  application_deadline: string | null;
  tuition_fee_eur: string | null;
  docs_ready: number;
  docs_total: number;
  submitted_at: string | null;
  created_at: string;
}

export interface ApplicationDetail extends Application {
  checklist: ChecklistItem[];
  motivation_letter: string;
  studyinfo_reference: string;
  notes: string;
  decision_at: string | null;
  /** Deep link to this programme on Studyinfo.fi (programme page or pre-filled search). */
  studyinfo_url: string;
}

export interface DocumentInfo {
  id: number;
  doc_type: DocType;
  status: "uploaded" | "ai_reviewed" | "issues_found" | "verified";
  filename: string;
  expires_at: string | null;
  uploaded_at: string;
}

/** Start an application for a programme (usually from a match). */
export function createApplication(program: number) {
  return request<ApplicationDetail>("/applications/", post({ program }));
}

export function getApplications() {
  return request<Application[]>("/applications/");
}

export function getApplication(id: number) {
  return request<ApplicationDetail>(`/applications/${id}/`);
}

export function updateApplication(
  id: number,
  patch: Partial<Pick<ApplicationDetail, "motivation_letter" | "notes" | "priority" | "studyinfo_reference">>,
) {
  return request<ApplicationDetail>(`/applications/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function setApplicationStatus(id: number, status: ApplicationStatus) {
  return request<ApplicationDetail>(`/applications/${id}/status/`, post({ status }));
}

// ─── Documents ───────────────────────────────────────────────────────────────

/** Multipart upload — must NOT set Content-Type so fetch writes the boundary. */
export async function uploadDocument(
  docType: DocType,
  file: { uri: string; name: string; mimeType?: string },
) {
  const form = new FormData();
  form.append("doc_type", docType);
  if (Platform.OS === "web") {
    // On web the picker URI is a blob/data URL — convert to a real Blob.
    const blob = await (await fetch(file.uri)).blob();
    form.append("file", new File([blob], file.name, { type: file.mimeType }));
  } else {
    // React Native's FormData takes the {uri, name, type} shape.
    form.append("file", {
      uri: file.uri,
      name: file.name,
      type: file.mimeType ?? "application/octet-stream",
    } as unknown as Blob);
  }
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const res = await fetch(`${API_URL}${API_VERSION_PREFIX}/documents/`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  });
  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(res.status, body);
  }
  return (await res.json()) as DocumentInfo;
}

export function getDocuments() {
  return request<DocumentInfo[]>("/documents/");
}

export function deleteDocument(id: number) {
  return request<void>(`/documents/${id}/`, { method: "DELETE" });
}

/** URL the app opens to view a document (redirects to a signed URL on R2). */
export function documentDownloadUrl(id: number) {
  return `${API_URL}${API_VERSION_PREFIX}/documents/${id}/download/`;
}

// ─── Notifications ───────────────────────────────────────────────────────────

export type NotificationCategory =
  | "reminder"
  | "advisor"
  | "news"
  | "update"
  | "system"
  | "document"
  | "application"
  | "visa";

export interface AppNotification {
  id: number;
  category: NotificationCategory;
  title: string;
  body: string;
  /** Deep-link payload, e.g. { type: "task", task_id: 7 }. */
  data: Record<string, unknown>;
  created_at: string;
  read_at: string | null;
}

export interface NotificationPage {
  unread_count: number;
  has_more: boolean;
  results: AppNotification[];
}

/** The inbox, newest first; pass `before` (an id) to page back in history. */
export function getNotifications(before?: number) {
  const qs = before !== undefined ? `?before=${before}` : "";
  return request<NotificationPage>(`/notifications/${qs}`);
}

export function markNotificationsRead(payload: { ids?: number[]; all?: boolean }) {
  return request<{ marked_read: number }>("/notifications/read/", post(payload));
}

/** Register this device's Expo push token so the backend can reach it. */
export function registerDevice(token: string, platform: "ios" | "android") {
  return request<void>("/devices/", post({ token, platform }));
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
