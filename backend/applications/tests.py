"""Matching-engine accuracy tests.

Born from a July 2026 accuracy scan: matches must track the CURRENT profile
(profile edits re-match), never promise affordability for an unknown price,
treat budget 0 and blank identically, and never recommend a program whose
application window has closed.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from students.models import Student
from universities.models import Program, University

from .models import Match
from .services import match_programs_for_student

User = get_user_model()


def make_program(uni, name, **overrides):
    fields = dict(
        university=uni, name=name, degree_level="masters", field_of_study="IT",
        intake="september", tuition_fee_eur=10000,
    )
    fields.update(overrides)
    return Program.objects.create(**fields)


class MatchFilterTests(APITestCase):
    def setUp(self):
        self.uni = University.objects.create(
            name="Aalto", institution_type="university", city="Espoo"
        )
        self.student = Student.objects.create(
            user=User.objects.create_user(email="m@example.com"),
            study_level="masters", field_of_study="IT", budget_eur_per_year=12000,
        )

    def matched(self):
        match_programs_for_student(self.student.pk)
        return set(
            Match.objects.filter(student=self.student).values_list("program__name", flat=True)
        )

    def test_unknown_fee_is_not_affordable(self):
        # NULL fee must not slip past the budget cap (SQL NULL comparisons
        # made `exclude(fee__gt=budget)` keep it).
        make_program(self.uni, "Known fee", tuition_fee_eur=9000)
        make_program(self.uni, "Unknown fee", tuition_fee_eur=None)
        self.assertEqual(self.matched(), {"Known fee"})

    def test_budget_zero_means_tuition_free_only_like_blank(self):
        make_program(self.uni, "Free", tuition_fee_eur=0)
        make_program(self.uni, "Cheap", tuition_fee_eur=1000)
        make_program(self.uni, "Unknown fee", tuition_fee_eur=None)

        self.student.budget_eur_per_year = 0
        self.student.save()
        zero = self.matched()

        self.student.budget_eur_per_year = None
        self.student.save()
        blank = self.matched()

        self.assertEqual(zero, {"Free"})
        self.assertEqual(zero, blank)  # 0 and blank are the same intent

    def test_passed_deadline_disqualifies_program(self):
        today = timezone.localdate()
        make_program(self.uni, "Closed", application_deadline=today - timedelta(days=1))
        make_program(self.uni, "Open", application_deadline=today + timedelta(days=30))
        make_program(self.uni, "Deadline unknown", application_deadline=None)
        # Closes today = still open.
        make_program(self.uni, "Closes today", application_deadline=today)
        self.assertEqual(self.matched(), {"Open", "Deadline unknown", "Closes today"})

    def test_stale_score_not_credited_after_status_reset(self):
        # Score lingers after the student flips status back to not-taken —
        # the engine must treat them as having no score (REACH below the bar).
        requiring = make_program(self.uni, "Needs 6.5", min_ielts_score="6.5")

        self.student.language_test_status = "taken"
        self.student.language_test = "ielts"
        self.student.language_test_score = "7.0"
        self.student.save()
        match_programs_for_student(self.student.pk)
        self.assertNotEqual(Match.objects.get(program=requiring).fit, Match.Fit.REACH)

        self.student.language_test_status = "not_taken"
        self.student.save()  # score field still holds "7.0"
        match_programs_for_student(self.student.pk)
        self.assertEqual(Match.objects.get(program=requiring).fit, Match.Fit.REACH)


class AcademicStrengthScoringTests(APITestCase):
    """Grades are a scoring signal (Awais's product decision, July 2026):
    exceptional profiles — ≥95% marks or GPA ≥3.5 — must move the match score
    drastically, reaching 100 on a well-fitting program."""

    def setUp(self):
        self.uni = University.objects.create(
            name="Aalto", institution_type="university", city="Espoo"
        )
        # A well-fitting program: clears IELTS with headroom, matching intake,
        # tuition-free → 50 +20 +10 +5 = 85 before grades.
        self.program = make_program(
            self.uni, "Well-fitting", tuition_fee_eur=0, min_ielts_score="6.5",
        )

    def score_for(self, **profile):
        student = Student.objects.create(
            user=User.objects.create_user(email=f"g{Student.objects.count()}@example.com"),
            study_level="masters", field_of_study="IT", budget_eur_per_year=None,
            language_test_status="taken", language_test="ielts",
            language_test_score="7.5", intake="september",
            **profile,
        )
        match_programs_for_student(student.pk)
        return Match.objects.get(student=student, program=self.program).score

    def test_gpa_3_5_or_above_reaches_100(self):
        self.assertEqual(self.score_for(grade_scale="gpa_4", grades="3.5"), 100)
        self.assertEqual(self.score_for(grade_scale="gpa_4", grades="3.9"), 100)

    def test_95_percent_marks_reach_100(self):
        self.assertEqual(self.score_for(grade_scale="percentage", grades="95"), 100)

    def test_a_star_reaches_100(self):
        self.assertEqual(self.score_for(grade_scale="letter", grades="A*"), 100)

    def test_band_ladder_separates_profiles(self):
        # A mid-fit program (paid, January intake → no +10/+5) shows the full
        # ladder without the 100 clamp flattening it: base 50 + IELTS 20 = 70.
        mid = make_program(
            self.uni, "Mid-fit", tuition_fee_eur=0, intake="january",
            min_ielts_score="6.5",
        )
        def mid_score(**profile):
            s = Student.objects.create(
                user=User.objects.create_user(email=f"l{Student.objects.count()}@example.com"),
                study_level="masters", field_of_study="IT", budget_eur_per_year=None,
                language_test_status="taken", language_test="ielts",
                language_test_score="7.5", intake="september", **profile,
            )
            match_programs_for_student(s.pk)
            return Match.objects.get(student=s, program=mid).score

        none = mid_score()                                          # 75
        good = mid_score(grade_scale="gpa_4", grades="2.7")         # +8
        strong = mid_score(grade_scale="percentage", grades="88")   # +15
        exceptional = mid_score(grade_scale="gpa_4", grades="3.8")  # +25
        self.assertEqual([none, good, strong, exceptional], [75, 83, 90, 100])

    def test_weak_grades_are_not_penalized(self):
        # Encouragement-first: low grades add nothing but subtract nothing.
        self.assertEqual(self.score_for(grade_scale="gpa_4", grades="1.8"),
                         self.score_for())


class ProfileEditRematchTests(APITestCase):
    """The Profile screen promises 'changing these updates your matches' —
    hold the API to it."""

    def setUp(self):
        self.uni = University.objects.create(
            name="LUT", institution_type="university", city="Lappeenranta"
        )
        self.user = User.objects.create_user(email="edit@example.com")
        self.student = Student.objects.create(
            user=self.user, study_level="masters", field_of_study="IT",
            budget_eur_per_year=5000,
        )
        self.cheap = make_program(self.uni, "Cheap", tuition_fee_eur=4000)
        self.pricey = make_program(self.uni, "Pricey", tuition_fee_eur=14000)
        match_programs_for_student(self.student.pk)
        self.client.force_authenticate(self.user)

    def names(self):
        return set(
            Match.objects.filter(student=self.student).values_list("program__name", flat=True)
        )

    def test_budget_edit_regenerates_matches(self):
        self.assertEqual(self.names(), {"Cheap"})
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.patch(reverse("profile"), {"budget_eur_per_year": 15000})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.names(), {"Cheap", "Pricey"})  # matches now current

    def test_language_score_edit_regenerates_matches(self):
        with patch("students.views.match_programs_task.delay") as task:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.patch(
                    reverse("profile"),
                    {"language_test_status": "taken", "language_test": "ielts",
                     "language_test_score": "7.5"},
                )
        task.assert_called_once_with(self.student.pk)

    def test_grades_edit_regenerates_matches(self):
        # Grades are a scoring signal now — editing them must re-rank.
        with patch("students.views.match_programs_task.delay") as task:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.patch(
                    reverse("profile"), {"grade_scale": "gpa_4", "grades": "3.8"}
                )
        task.assert_called_once_with(self.student.pk)

    def test_irrelevant_edit_does_not_rematch(self):
        # A name change must not churn the match table.
        with patch("students.views.match_programs_task.delay") as task:
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.patch(
                    reverse("profile"), {"first_name": "Ayesha", "home_city": "Lahore"}
                )
        self.assertEqual(resp.status_code, 200)
        task.assert_not_called()

    def test_noop_value_does_not_rematch(self):
        # PATCHing a relevant field with its existing value changes nothing.
        with patch("students.views.match_programs_task.delay") as task:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.patch(reverse("profile"), {"budget_eur_per_year": 5000})
        task.assert_not_called()
