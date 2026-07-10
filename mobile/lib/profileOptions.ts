/**
 * Option lists for the profile/onboarding enum fields, shared by the
 * Get Started form and the Profile editor so labels and backend values
 * never drift between the two.
 */
import type { Intake, LanguageTestStatus, Stage, StudyLevel } from "./api";

// "Last completed education" drives study_level: the backend model encodes
// exactly this pairing (UNDERGRADUATE = "Undergraduate (FSc/A-Levels)",
// MASTERS = "Masters (Bachelor's degree)").
export const EDUCATION_LEVELS: { value: StudyLevel; label: string }[] = [
  { value: "masters", label: "Bachelor's degree" },
  { value: "undergraduate", label: "FSc / A-Levels" },
];

export const TEST_STATUSES: { value: LanguageTestStatus; label: string }[] = [
  { value: "not_taken", label: "Not taken yet" },
  { value: "booked", label: "Test booked" },
  { value: "taken", label: "Score available" },
];

export const INTAKES: { value: Intake; label: string }[] = [
  { value: "september", label: "September" },
  { value: "january", label: "January" },
];

// Programme catalogue taxonomy (from the Opintopolku ingester) — matching
// filters `field_of_study__icontains`, so these must align with the backend.
export const FIELDS = ["IT", "Business", "Design", "Engineering"].map((f) => ({
  value: f,
  label: f,
}));

// Years a student can realistically target for the chosen intake.
export const INTAKE_YEARS = (() => {
  const y = new Date().getFullYear();
  return [y, y + 1, y + 2].map((v) => ({ value: String(v), label: String(v) }));
})();

export const STAGES: { value: Stage; label: string }[] = [
  { value: "exploring", label: "Just exploring" },
  { value: "ready", label: "Ready to apply" },
  { value: "applied", label: "Already applied" },
];
