from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Student

User = get_user_model()


class ProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="s@example.com", password="SafePass!2026")

    def test_profile_requires_auth(self):
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_created_lazily_on_first_access(self):
        self.assertFalse(Student.objects.filter(user=self.user).exists())
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "s@example.com")
        self.assertEqual(resp.data["tier"], "free")
        self.assertTrue(Student.objects.filter(user=self.user).exists())

    def test_onboarding_profile_update(self):
        self.client.force_authenticate(self.user)
        resp = self.client.patch(
            reverse("profile"),
            {
                "study_level": "masters",
                "field_of_study": "Computer Science",
                "intake": "september",
                "intake_year": 2027,
                "stage": "exploring",
                "onboarding_completed": True,
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        student = Student.objects.get(user=self.user)
        self.assertEqual(student.study_level, "masters")
        self.assertTrue(student.onboarding_completed)

    def test_tier_is_read_only_via_api(self):
        self.client.force_authenticate(self.user)
        resp = self.client.patch(reverse("profile"), {"tier": "premium"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.tier, "free")


class SchemaRelationTests(APITestCase):
    """Smoke-test the cross-app relationships in the domain schema."""

    def test_full_journey_object_graph(self):
        from applications.models import Application, Visa
        from chat.models import Conversation, Message
        from students.models import Accommodation, Flight, Task
        from universities.models import Campus, Program, University

        user = User.objects.create_user(email="j@example.com", password="SafePass!2026")
        student = Student.objects.create(user=user, intake="september", intake_year=2027)

        uni = University.objects.create(
            name="Aalto University", institution_type="university", city="Espoo"
        )
        campus = Campus.objects.create(university=uni, name="Otaniemi", city="Espoo")
        program = Program.objects.create(
            university=uni, campus=campus, name="Computer Science",
            degree_level="masters", field_of_study="IT", intake="september",
            tuition_fee_eur=15000,
        )

        app = Application.objects.create(student=student, program=program, fit="good_fit")
        visa = Visa.objects.create(student=student, application=app)

        task = Task.objects.create(student=student, phase=4, title="Book embassy appointment")
        student.reminders.create(task=task, title="Embassy in 3 days", remind_at="2027-01-01T09:00:00Z")

        Accommodation.objects.create(student=student, kind="student_housing", provider="HOAS")
        Flight.objects.create(
            student=student, airline="Qatar Airways", flight_number="QR633",
            depart_airport="ISB", arrive_airport="HEL",
            depart_at="2027-08-20T03:00:00Z", arrive_at="2027-08-20T14:30:00Z",
        )

        convo = Conversation.objects.create(student=student, phase_context=4)
        Message.objects.create(conversation=convo, role="user", content="When do I register with DVV?")

        self.assertEqual(student.applications.count(), 1)
        self.assertEqual(student.visas.first(), visa)
        self.assertEqual(uni.programs.first().applications.first().student, student)
        self.assertEqual(student.tasks.first().reminders.count(), 1)
        self.assertEqual(convo.messages.count(), 1)

    def test_cannot_apply_twice_to_same_program(self):
        from django.db import IntegrityError

        from applications.models import Application
        from universities.models import Program, University

        user = User.objects.create_user(email="d@example.com", password="SafePass!2026")
        student = Student.objects.create(user=user)
        uni = University.objects.create(name="LUT", institution_type="university", city="Lappeenranta")
        program = Program.objects.create(
            university=uni, name="Software Engineering", degree_level="masters",
            field_of_study="IT", intake="september",
        )
        Application.objects.create(student=student, program=program)
        with self.assertRaises(IntegrityError):
            Application.objects.create(student=student, program=program)
