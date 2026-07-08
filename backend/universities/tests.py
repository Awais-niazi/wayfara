from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from applications.models import Match
from students.models import Student

from .models import Program, University, UniversityProfile

User = get_user_model()


class UniversityProfileMatchTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="s@example.com")
        self.student = Student.objects.create(user=self.user)
        self.client.force_authenticate(self.user)

    def _match(self, uni):
        program = Program.objects.create(
            university=uni, name="CS", degree_level="masters", field_of_study="IT",
            intake="september", tuition_fee_eur=15000,
        )
        return Match.objects.create(student=self.student, program=program, fit="good_fit", score=70)

    def test_match_without_profile_has_null_kb_fields(self):
        uni = University.objects.create(name="Plain Uni", institution_type="university", city="X")
        self._match(uni)
        resp = self.client.get(reverse("matches"))
        row = resp.data[0]
        self.assertIsNone(row["world_ranking"])
        self.assertFalse(row["featured"])
        self.assertFalse(row["data_verified"])

    def test_match_with_profile_exposes_kb_fields(self):
        uni = University.objects.create(name="Aalto", institution_type="university", city="Espoo")
        UniversityProfile.objects.create(
            university=uni, featured=True, world_ranking=114,
            ranking_system="qs", operational_verified=True, needs_review=False,
        )
        self._match(uni)
        resp = self.client.get(reverse("matches"))
        row = resp.data[0]
        self.assertEqual(row["world_ranking"], 114)
        self.assertTrue(row["featured"])
        self.assertTrue(row["data_verified"])
        self.assertEqual(row["tuition_fee_eur"], "15000.00")

    def test_profile_is_one_to_one(self):
        from django.db import IntegrityError

        uni = University.objects.create(name="Solo", institution_type="university", city="X")
        UniversityProfile.objects.create(university=uni)
        with self.assertRaises(IntegrityError):
            UniversityProfile.objects.create(university=uni)
