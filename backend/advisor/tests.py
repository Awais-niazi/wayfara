from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from students.models import Document, Student

User = get_user_model()


class AdvisorActivationTests(APITestCase):
    def _make_advisor(self, email="adv@example.com"):
        user = User.objects.create_user(email=email, role=User.Role.ADVISOR)
        user.set_unusable_password()
        user.save(update_fields=["password"])
        return user

    def test_admin_action_sends_link_and_disables_password_login(self):
        # Simulate the admin provisioning action end result.
        advisor = self._make_advisor()
        from advisor.services import send_advisor_activation

        send_advisor_activation(advisor)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/activate/", mail.outbox[0].body)
        self.assertFalse(advisor.has_usable_password())

    def test_activation_sets_password_and_is_single_use(self):
        advisor = self._make_advisor()
        uid = urlsafe_base64_encode(force_bytes(advisor.pk))
        token = default_token_generator.make_token(advisor)
        url = reverse("advisor_activate")

        resp = self.client.post(
            url, {"uid": uid, "token": token, "password": "AdvisorPass!2026"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        advisor.refresh_from_db()
        self.assertTrue(advisor.check_password("AdvisorPass!2026"))

        # Token is spent — setting the password changed the hash it derives from.
        resp = self.client.post(
            url, {"uid": uid, "token": token, "password": "Another!2026"}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activation_rejects_weak_password(self):
        advisor = self._make_advisor()
        uid = urlsafe_base64_encode(force_bytes(advisor.pk))
        token = default_token_generator.make_token(advisor)
        resp = self.client.post(
            reverse("advisor_activate"), {"uid": uid, "token": token, "password": "123"}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activation_link_cannot_target_a_student(self):
        student_user = User.objects.create_user(email="s@example.com")  # role=student
        uid = urlsafe_base64_encode(force_bytes(student_user.pk))
        token = default_token_generator.make_token(student_user)
        resp = self.client.post(
            reverse("advisor_activate"),
            {"uid": uid, "token": token, "password": "TryToHijack!2026"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        student_user.refresh_from_db()
        self.assertFalse(student_user.check_password("TryToHijack!2026"))


class AdvisorCaseloadTests(APITestCase):
    def setUp(self):
        self.adv1 = User.objects.create_user(email="adv1@example.com", role=User.Role.ADVISOR)
        self.adv2 = User.objects.create_user(email="adv2@example.com", role=User.Role.ADVISOR)
        self.mine = Student.objects.create(
            user=User.objects.create_user(email="mine@example.com"),
            assigned_advisor=self.adv1,
        )
        self.theirs = Student.objects.create(
            user=User.objects.create_user(email="theirs@example.com"),
            assigned_advisor=self.adv2,
        )
        self.unassigned = Student.objects.create(
            user=User.objects.create_user(email="free@example.com")
        )

    def test_student_cannot_reach_advisor_surface(self):
        student = User.objects.create_user(email="learner@example.com")
        self.client.force_authenticate(student)
        resp = self.client.get(reverse("advisor_students"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_advisor_sees_only_own_caseload(self):
        self.client.force_authenticate(self.adv1)
        resp = self.client.get(reverse("advisor_students"))
        emails = {row["email"] for row in resp.data}
        self.assertEqual(emails, {"mine@example.com"})

    def test_advisor_cannot_open_another_advisors_student(self):
        self.client.force_authenticate(self.adv1)
        resp = self.client.get(reverse("advisor_student_detail", args=[self.theirs.pk]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_advisor_can_open_own_student(self):
        self.client.force_authenticate(self.adv1)
        resp = self.client.get(reverse("advisor_student_detail", args=[self.mine.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "mine@example.com")


class AdvisorDocumentAccessTests(APITestCase):
    def setUp(self):
        self.advisor = User.objects.create_user(email="adv@example.com", role=User.Role.ADVISOR)
        self.other = User.objects.create_user(email="other@example.com", role=User.Role.ADVISOR)
        self.student = Student.objects.create(
            user=User.objects.create_user(email="s@example.com"),
            assigned_advisor=self.advisor,
        )
        self.doc = Document.objects.create(
            student=self.student,
            doc_type="passport",
            file=SimpleUploadedFile("passport.pdf", b"%PDF-1.4 secret", content_type="application/pdf"),
        )

    def test_assigned_advisor_can_download(self):
        self.client.force_authenticate(self.advisor)
        resp = self.client.get(reverse("advisor_document_download", args=[self.doc.pk]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(resp.streaming_content), b"%PDF-1.4 secret")

    def test_unassigned_advisor_gets_404_not_the_file(self):
        self.client.force_authenticate(self.other)
        resp = self.client.get(reverse("advisor_document_download", args=[self.doc.pk]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def tearDown(self):
        self.doc.file.delete(save=False)
