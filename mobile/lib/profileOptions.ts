/**
 * Option lists for the profile/onboarding enum fields, shared by the
 * Get Started form and the Profile editor so labels and backend values
 * never drift between the two.
 */
import type {
  GradeScale,
  Intake,
  LanguageTest,
  LanguageTestStatus,
  Stage,
  StudyLevel,
} from "./api";

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

export const LANGUAGE_TESTS: { value: LanguageTest; label: string }[] = [
  { value: "ielts", label: "IELTS" },
  { value: "toefl", label: "TOEFL iBT" },
  { value: "pte", label: "PTE Academic" },
  { value: "duolingo", label: "Duolingo" },
];

export const GRADE_SCALES: { value: GradeScale; label: string }[] = [
  { value: "gpa_4", label: "GPA (out of 4)" },
  { value: "percentage", label: "Percentage" },
  { value: "letter", label: "Letter grade" },
];

// Adaptive value-input props per grade scale / test, shared by the onboarding
// wizard and the profile editor so both behave identically.
export const GRADE_INPUT: Record<
  GradeScale,
  {
    placeholder: string;
    keyboardType: "decimal-pad" | "number-pad" | "default";
    maxLength: number;
    hint: string;
  }
> = {
  gpa_4: { placeholder: "3.4", keyboardType: "decimal-pad", maxLength: 4, hint: "Between 0.5 and 4.0" },
  percentage: { placeholder: "85", keyboardType: "number-pad", maxLength: 3, hint: "Whole number, 0–100" },
  letter: { placeholder: "A*", keyboardType: "default", maxLength: 2, hint: "A–E, optionally *, + or -" },
};

export const TEST_PLACEHOLDER: Record<LanguageTest, string> = {
  ielts: "7.0",
  toefl: "100",
  pte: "65",
  duolingo: "120",
};

export const TEST_RANGE_HINT: Record<LanguageTest, string> = {
  ielts: "0–9.0 (half steps)",
  toefl: "0–120",
  pte: "10–90",
  duolingo: "10–160",
};

// Per-test valid score ranges, mirrored from students/validators.py so the app
// gives the same immediate feedback the server would enforce. `half` = only
// .0/.5 steps allowed (IELTS); otherwise whole numbers.
export const TEST_RANGES: Record<LanguageTest, { min: number; max: number; half: boolean }> = {
  ielts: { min: 0, max: 9, half: true },
  toefl: { min: 0, max: 120, half: false },
  pte: { min: 10, max: 90, half: false },
  duolingo: { min: 10, max: 160, half: false },
};

export const GPA_MIN = 0.5;
export const GPA_MAX = 4;
export const BUDGET_MIN = 1000;
export const BUDGET_MAX = 100000;
const LETTER_GRADE_RE = /^[A-E][*+-]?$/;


/** Client-side mirror of the server's semantic validation. Returns an error
 *  string for the field, or null when the value is acceptable. Empty optional
 *  values pass — the server treats blank as "not provided". */
export function gradeError(scale: GradeScale | "", grades: string): string | null {
  const v = grades.trim();
  if (v === "") return null;
  if (scale === "") return "Pick a grade type first.";
  if (scale === "gpa_4") {
    const n = Number(v);
    if (!Number.isFinite(n) || n < GPA_MIN || n > GPA_MAX)
      return `GPA must be between ${GPA_MIN} and ${GPA_MAX}.`;
  } else if (scale === "percentage") {
    const n = Number(v);
    if (!Number.isInteger(n) || n < 0 || n > 100)
      return "Percentage must be a whole number from 0 to 100.";
  } else if (scale === "letter") {
    if (!LETTER_GRADE_RE.test(v.toUpperCase()))
      return "Enter a single grade A–E, optionally with *, + or - (e.g. A*, B+, C).";
  }
  return null;
}

export function testScoreError(test: LanguageTest | "", score: string): string | null {
  const v = score.trim();
  if (v === "") return null;
  if (test === "") return "Pick which test you took first.";
  const { min, max, half } = TEST_RANGES[test];
  const n = Number(v);
  if (!Number.isFinite(n) || n < min || n > max)
    return `Score must be between ${min} and ${max}.`;
  if (half) {
    if (Math.round(n * 2) !== n * 2) return "Scores go in half-point steps (e.g. 6.5, 7.0).";
  } else if (!Number.isInteger(n)) {
    return "Score must be a whole number.";
  }
  return null;
}

export function budgetError(budget: string): string | null {
  const v = budget.trim();
  if (v === "") return null;
  const n = Number(v);
  if (n === 0) return null; // tuition-free intent
  if (!Number.isInteger(n) || n < BUDGET_MIN || n > BUDGET_MAX)
    return `Enter a realistic budget (€${BUDGET_MIN.toLocaleString()}–€${BUDGET_MAX.toLocaleString()}), or leave blank.`;
  return null;
}

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
