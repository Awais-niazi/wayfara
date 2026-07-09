from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from rest_framework.test import APITestCase

from applications.models import Match
from students.models import Student

from .models import Program, University, UniversityProfile

User = get_user_model()


class CatalogDiscoveryTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.uni = University.objects.create(
            name="Aalto University", institution_type="university", city="Espoo"
        )
        UniversityProfile.objects.create(
            university=self.uni, featured=True, world_ranking=114,
            ranking_system="qs", ranking_year=2026, overview="Tech, business, design.",
            needs_review=False,
        )
        self.program = Program.objects.create(
            university=self.uni, name="CS", degree_level="masters",
            field_of_study="IT", intake="september", tuition_fee_eur=15000,
        )

    def test_list_is_public_and_exposes_kb_fields(self):
        resp = self.client.get(reverse("university_list"))
        self.assertEqual(resp.status_code, 200)
        row = resp.data[0]
        self.assertEqual(row["world_ranking"], 114)
        self.assertTrue(row["featured"])
        self.assertEqual(row["overview"], "Tech, business, design.")

    def test_unreviewed_overview_is_hidden(self):
        self.uni.profile.needs_review = True
        self.uni.profile.save()
        resp = self.client.get(reverse("university_list"))
        self.assertEqual(resp.data[0]["overview"], "")

    def test_second_request_is_served_from_cache(self):
        self.client.get(reverse("university_list"))  # prime
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("university_list"))
        self.assertEqual(len(ctx.captured_queries), 0)  # zero DB hits on cache hit

    def test_catalog_write_invalidates_cache(self):
        self.client.get(reverse("university_list"))  # prime
        # A new active programme's university should now be visible.
        University.objects.create(
            name="LUT University", institution_type="university", city="Lappeenranta"
        )
        resp = self.client.get(reverse("university_list"))
        names = {u["name"] for u in resp.data}
        self.assertIn("LUT University", names)

    def test_detail_lists_active_programs_only(self):
        Program.objects.create(
            university=self.uni, name="Retired", degree_level="masters",
            field_of_study="IT", intake="january", is_active=False,
        )
        resp = self.client.get(reverse("university_detail", args=[self.uni.pk]))
        self.assertEqual(resp.status_code, 200)
        names = {p["name"] for p in resp.data["programs"]}
        self.assertEqual(names, {"CS"})

    def test_inactive_university_is_404(self):
        self.uni.is_active = False
        self.uni.save()
        resp = self.client.get(reverse("university_detail", args=[self.uni.pk]))
        self.assertEqual(resp.status_code, 404)

    def tearDown(self):
        cache.clear()


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
