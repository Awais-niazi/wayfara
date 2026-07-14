from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from applications.models import Match
from universities.models import Program, University

from .models import Student

User = get_user_model()


def otp_code_from_email():
    """Pull the 6-digit code out of the most recent OTP email. Codes are
    hashed at rest, so the email is the only place the plaintext exists —
    which is exactly how a real user gets it."""
    import re

    match = re.search(r"\b(\d{6})\b", mail.outbox[-1].body)
    assert match, "No 6-digit code found in the OTP email"
    return match.group(1)

FORM = {
    "email": "applicant@example.com",
    "study_level": "masters",
    "field_of_study": "IT",
    "grade_scale": "gpa_4",
    "grades": "3.4",
    "language_test_status": "taken",
    "language_test": "ielts",
    "language_test_score": "7.0",
    "budget_eur_per_year": 12000,
    "intake": "september",
    "intake_year": 2027,
    "stage": "exploring",
}


def seed_programs():
    uni = University.objects.create(name="Aalto University", institution_type="university", city="Espoo")
    lut = University.objects.create(name="LUT University", institution_type="university", city="Lappeenranta")
    fits = Program.objects.create(
        university=uni, name="Computer Science", degree_level="masters", field_of_study="IT",
        intake="september", tuition_fee_eur=12000, min_ielts_score="6.5", acceptance_rate="25",
    )
    too_expensive = Program.objects.create(
        university=uni, name="Data Science", degree_level="masters", field_of_study="IT",
        intake="september", tuition_fee_eur=18000,
    )
    wrong_level = Program.objects.create(
        university=lut, name="Software Engineering", degree_level="bachelors", field_of_study="IT",
        intake="september", tuition_fee_eur=9000,
    )
    reach = Program.objects.create(
        university=lut, name="AI & Machine Learning", degree_level="masters", field_of_study="IT",
        intake="september", tuition_fee_eur=10000, min_ielts_score="7.5", acceptance_rate="8",
    )
    return fits, too_expensive, wrong_level, reach


class OnboardingFlowTests(APITestCase):
    def submit_form(self, **overrides):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("onboarding"), {**FORM, **overrides}, format="json")

    def test_full_flow_form_to_matches(self):
        fits, too_expensive, wrong_level, reach = seed_programs()

        resp = self.submit_form()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Account created passwordless; student profile stored
        user = User.objects.get(email="applicant@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(user.student.onboarding_completed)

        # OTP email went out
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verification code", mail.outbox[0].body)

        # Background matching ran (sync mode): filters applied
        matched_programs = set(
            Match.objects.filter(student=user.student).values_list("program_id", flat=True)
        )
        self.assertIn(fits.pk, matched_programs)
        self.assertIn(reach.pk, matched_programs)
        self.assertNotIn(too_expensive.pk, matched_programs)
        self.assertNotIn(wrong_level.pk, matched_programs)

        # Fit ratings: good headroom vs below-the-bar selective program
        self.assertNotEqual(Match.objects.get(program=fits).fit, "reach")
        self.assertEqual(Match.objects.get(program=reach).fit, "reach")

        # Verify OTP -> tokens
        code = otp_code_from_email()
        resp = self.client.post(
            reverse("otp_verify"), {"email": "applicant@example.com", "code": code}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        access = resp.data["access"]
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

        # Authenticated matches endpoint returns them, best first
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.get(reverse("matches"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)
        scores = [float(m["score"]) for m in resp.data]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(resp.data[0]["university"], "Aalto University")

    def test_resubmission_updates_profile_not_duplicate_account(self):
        seed_programs()
        self.submit_form()
        resp = self.submit_form(field_of_study="Computer Science", budget_eur_per_year=15000)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(email="applicant@example.com").count(), 1)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(Student.objects.get().budget_eur_per_year, 15000)

    def test_no_budget_means_tuition_free_only(self):
        seed_programs()
        uni = University.objects.get(name="LUT University")
        free = Program.objects.create(
            university=uni, name="ICT (tuition-free track)", degree_level="masters",
            field_of_study="IT", intake="september", tuition_fee_eur=0,
        )
        self.submit_form(budget_eur_per_year=None)
        student = Student.objects.get()
        matched = set(Match.objects.filter(student=student).values_list("program_id", flat=True))
        self.assertEqual(matched, {free.pk})

    def test_wrong_otp_rejected_and_attempts_limited(self):
        self.submit_form()
        user = User.objects.get(email="applicant@example.com")
        for _ in range(5):
            resp = self.client.post(
                reverse("otp_verify"), {"email": user.email, "code": "000000"}
            )
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # Correct code now rejected too: attempt limit reached
        code = otp_code_from_email()
        resp = self.client.post(reverse("otp_verify"), {"email": user.email, "code": code})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_otp_request_does_not_leak_account_existence(self):
        resp = self.client.post(reverse("otp_request"), {"email": "nobody@example.com"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)


class AcademicValidationTests(APITestCase):
    """Illogical academic values are rejected at onboarding — the whole form
    fails, no account is created."""

    def _submit(self, **overrides):
        return self.client.post(reverse("onboarding"), {**FORM, **overrides}, format="json")

    def _assert_rejected(self, field, **overrides):
        resp = self._submit(**overrides)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(field, resp.data)
        self.assertFalse(User.objects.filter(email="applicant@example.com").exists())

    def test_ielts_score_above_9_rejected(self):
        self._assert_rejected("language_test_score", language_test="ielts", language_test_score="11")

    def test_ielts_non_half_step_rejected(self):
        self._assert_rejected("language_test_score", language_test="ielts", language_test_score="7.3")

    def test_toefl_in_range_accepted_and_converted_for_matching(self):
        seed_programs()
        with self.captureOnCommitCallbacks(execute=True):
            resp = self._submit(language_test="toefl", language_test_score="100")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        s = Student.objects.get()
        self.assertEqual(s.language_test, "toefl")
        # TOEFL 100 ≈ IELTS 7.0 — clears the 6.5 program, not the 7.5 reach.
        self.assertTrue(Match.objects.filter(student=s).exists())

    def test_toefl_above_120_rejected(self):
        self._assert_rejected("language_test_score", language_test="toefl", language_test_score="150")

    def test_gpa_above_4_rejected(self):
        self._assert_rejected("grades", grade_scale="gpa_4", grades="7.2")

    def test_percentage_above_100_rejected(self):
        self._assert_rejected("grades", grade_scale="percentage", grades="150")

    def test_letter_grade_out_of_range_rejected(self):
        self._assert_rejected("grades", grade_scale="letter", grades="Z")

    def test_letter_grade_valid_accepted(self):
        resp = self._submit(grade_scale="letter", grades="A*")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_grades_without_scale_rejected(self):
        self._assert_rejected("grade_scale", grade_scale="", grades="3.4")

    def test_absurd_budget_rejected(self):
        self._assert_rejected("budget_eur_per_year", budget_eur_per_year=30)

    def test_zero_budget_accepted_as_tuition_free(self):
        resp = self._submit(budget_eur_per_year=0)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
