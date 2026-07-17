"""Application workspace tests: create-from-match, checklist (baseline vs
curated), status ladder + milestone notifications, scoping."""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from notifications.models import Notification
from students.models import Document, Student
from universities.models import Program, RequiredDocument, University

from .models import Application, Match

User = get_user_model()


def make_pdf(name="doc.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")


class ApplicationWorkspaceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="app@example.com")
        self.student = Student.objects.create(user=self.user, onboarding_completed=True)
        self.uni = University.objects.create(
            name="Aalto", institution_type="university", city="Espoo"
        )
        self.program = Program.objects.create(
            university=self.uni, name="CS", degree_level="masters",
            field_of_study="IT", intake="september", tuition_fee_eur=12000,
        )
        self.client.force_authenticate(self.user)

    def apply(self, program=None):
        return self.client.post(
            reverse("applications"), {"program": (program or self.program).pk}, format="json"
        )

    def test_create_copies_fit_from_match(self):
        Match.objects.create(
            student=self.student, program=self.program, fit="reach", score=55
        )
        resp = self.apply()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["fit"], "reach")
        self.assertEqual(resp.data["status"], "shortlisted")

    def test_duplicate_application_rejected(self):
        self.apply()
        resp = self.apply()
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("program", resp.data)
        self.assertEqual(Application.objects.count(), 1)

    def test_inactive_program_rejected(self):
        self.program.is_active = False
        self.program.save()
        resp = self.apply()
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_never_leaks_across_students(self):
        self.apply()
        other = User.objects.create_user(email="other@example.com")
        Student.objects.create(user=other)
        self.client.force_authenticate(other)
        resp = self.client.get(reverse("applications"))
        self.assertEqual(resp.data, [])

    def test_checklist_baseline_and_fulfilment(self):
        self.apply()
        app_id = Application.objects.get().pk
        resp = self.client.get(reverse("application_detail", args=[app_id]))
        checklist = resp.data["checklist"]
        self.assertEqual(len(checklist), 7)  # baseline set incl. optional LOR
        self.assertFalse(any(row["fulfilled"] for row in checklist))

        # Upload a transcript -> that row flips; docs_ready counts required only.
        Document.objects.create(
            student=self.student, doc_type="transcript", file=make_pdf()
        )
        resp = self.client.get(reverse("application_detail", args=[app_id]))
        by_type = {row["doc_type"]: row for row in resp.data["checklist"]}
        self.assertTrue(by_type["transcript"]["fulfilled"])
        self.assertEqual(resp.data["docs_ready"], 1)
        self.assertEqual(resp.data["docs_total"], 6)  # LOR is optional

    def test_motivation_letter_text_satisfies_checklist(self):
        self.apply()
        app_id = Application.objects.get().pk
        self.client.patch(
            reverse("application_detail", args=[app_id]),
            {"motivation_letter": "I want to study CS at Aalto because..."},
            format="json",
        )
        resp = self.client.get(reverse("application_detail", args=[app_id]))
        by_type = {row["doc_type"]: row for row in resp.data["checklist"]}
        self.assertTrue(by_type["motivation_letter"]["fulfilled"])

    def test_curated_requirements_replace_baseline(self):
        RequiredDocument.objects.create(
            program=self.program, doc_type="language_certificate",
            notes="IELTS Academic only, min 6.5",
        )
        RequiredDocument.objects.create(program=self.program, doc_type="cv")
        self.apply()
        app_id = Application.objects.get().pk
        checklist = self.client.get(
            reverse("application_detail", args=[app_id])
        ).data["checklist"]
        self.assertEqual(
            {row["doc_type"] for row in checklist}, {"language_certificate", "cv"}
        )
        by_type = {row["doc_type"]: row for row in checklist}
        self.assertEqual(by_type["language_certificate"]["notes"], "IELTS Academic only, min 6.5")

    def test_status_ladder_stamps_and_notifies(self):
        self.apply()
        app_id = Application.objects.get().pk
        url = reverse("application_status", args=[app_id])

        resp = self.client.post(url, {"status": "submitted"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        application = Application.objects.get()
        self.assertIsNotNone(application.submitted_at)

        self.client.post(url, {"status": "offer_received"}, format="json")
        application.refresh_from_db()
        self.assertIsNotNone(application.decision_at)

        notes = Notification.objects.filter(
            user=self.user, category=Notification.Category.APPLICATION
        )
        self.assertEqual(notes.count(), 2)  # submitted + offer
        self.assertIn("Offer received", notes.first().title)

    def test_no_op_and_backwards_transitions_rejected(self):
        self.apply()
        app_id = Application.objects.get().pk
        url = reverse("application_status", args=[app_id])
        resp = self.client.post(url, {"status": "shortlisted"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_touch_another_students_application(self):
        self.apply()
        app_id = Application.objects.get().pk
        stranger = User.objects.create_user(email="stranger@example.com")
        Student.objects.create(user=stranger)
        self.client.force_authenticate(stranger)
        self.assertEqual(
            self.client.get(reverse("application_detail", args=[app_id])).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(
                reverse("application_status", args=[app_id]),
                {"status": "submitted"},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )


class StudyinfoDeepLinkTests(APITestCase):
    """The gate button must never dump students on the Studyinfo homepage."""

    def setUp(self):
        self.user = User.objects.create_user(email="gate@example.com")
        self.student = Student.objects.create(user=self.user, onboarding_completed=True)
        self.uni = University.objects.create(
            name="LUT", institution_type="university", city="Lappeenranta"
        )
        self.client.force_authenticate(self.user)

    def _detail(self, program):
        app = Application.objects.create(student=self.student, program=program)
        return self.client.get(reverse("application_detail", args=[app.pk]))

    def test_scraped_program_links_to_its_studyinfo_page(self):
        program = Program.objects.create(
            university=self.uni, name="Software Engineering", degree_level="masters",
            field_of_study="IT", intake="september",
            external_source="opintopolku", external_id="1.2.246.562.13.999",
        )
        resp = self._detail(program)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp.data["studyinfo_url"],
            "https://opintopolku.fi/konfo/en/koulutus/1.2.246.562.13.999",
        )

    def test_manual_program_falls_back_to_prefilled_search(self):
        program = Program.objects.create(
            university=self.uni, name="Data Science & AI", degree_level="masters",
            field_of_study="IT", intake="september",
        )
        resp = self._detail(program)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp.data["studyinfo_url"],
            "https://opintopolku.fi/konfo/en/haku/Data%20Science%20%26%20AI",
        )
