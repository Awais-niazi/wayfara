/**
 * Shared profile-form plumbing for the Profile tab and the pushed
 * ProfileSection screens: the editable slice of the profile as form-friendly
 * strings, the API↔form mappers, and the changed-fields diff for PATCH.
 */
import type {
  GradeScale,
  Intake,
  LanguageTest,
  LanguageTestStatus,
  Profile,
  Stage,
  StudyLevel,
} from "./api";

/** Editable slice of the profile, all as form-friendly strings/enums. */
export interface FormState {
  first_name: string;
  last_name: string;
  phone: string;
  home_city: string;
  nationality: string;
  study_level: StudyLevel | "";
  field_of_study: string;
  grade_scale: GradeScale | "";
  grades: string;
  language_test_status: LanguageTestStatus | "";
  language_test: LanguageTest | "";
  language_test_score: string;
  budget: string; // numeric text input; "" = unset
  intake: Intake | "";
  intake_year: string; // "" = unset
  stage: Stage | "";
}

export function toForm(p: Profile): FormState {
  return {
    first_name: p.first_name,
    last_name: p.last_name,
    phone: p.phone,
    home_city: p.home_city,
    nationality: p.nationality,
    study_level: p.study_level,
    field_of_study: p.field_of_study,
    grade_scale: p.grade_scale,
    grades: p.grades,
    language_test_status: p.language_test_status,
    language_test: p.language_test,
    language_test_score: p.language_test_score,
    budget: p.budget_eur_per_year === null ? "" : String(p.budget_eur_per_year),
    intake: p.intake,
    intake_year: p.intake_year === null ? "" : String(p.intake_year),
    stage: p.stage,
  };
}

/** The PATCH body: only fields that differ from the loaded profile. */
export function diff(form: FormState, base: FormState): Partial<Profile> {
  const patch: Partial<Profile> = {};
  if (form.first_name !== base.first_name) patch.first_name = form.first_name.trim();
  if (form.last_name !== base.last_name) patch.last_name = form.last_name.trim();
  if (form.phone !== base.phone) patch.phone = form.phone.trim();
  if (form.home_city !== base.home_city) patch.home_city = form.home_city.trim();
  if (form.nationality !== base.nationality) patch.nationality = form.nationality.trim();
  if (form.study_level !== base.study_level) patch.study_level = form.study_level;
  if (form.field_of_study !== base.field_of_study) patch.field_of_study = form.field_of_study;
  if (form.grade_scale !== base.grade_scale) patch.grade_scale = form.grade_scale;
  if (form.grades !== base.grades) patch.grades = form.grades.trim();
  if (form.language_test_status !== base.language_test_status)
    patch.language_test_status = form.language_test_status;
  if (form.language_test !== base.language_test) patch.language_test = form.language_test;
  if (form.language_test_score !== base.language_test_score)
    patch.language_test_score = form.language_test_score.trim();
  if (form.budget !== base.budget)
    patch.budget_eur_per_year = form.budget.trim() === "" ? null : parseInt(form.budget, 10);
  if (form.intake !== base.intake) patch.intake = form.intake;
  if (form.intake_year !== base.intake_year)
    patch.intake_year = form.intake_year === "" ? null : parseInt(form.intake_year, 10);
  if (form.stage !== base.stage) patch.stage = form.stage;
  return patch;
}

/** Label for a value from a {value, label} options array. */
export const labelOf = (options: { value: string; label: string }[], value: string) =>
  options.find((o) => o.value === value)?.label ?? "";
