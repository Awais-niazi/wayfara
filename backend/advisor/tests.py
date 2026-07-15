from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from students.models import Document, Student

from .services import get_thread_for_student, post_message

User = get_user_model()


class AdvisorProvisioningTests(APITestCase):
    """Advisors are minted through Supabase (invite) + a local advisor row;
    they set their own password via Supabase, never through Django."""

    @patch("accounts.supabase.invite_user", return_value="11111111-1111-1111-1111-111111111111")
    def test_provision_creates_supabase_backed_advisor(self, mock_invite):
        from accounts.supabase import provision_advisor

        user, created = provision_advisor("new.advisor@example.com")
        mock_invite.assert_called_once_with("new.advisor@example.com")
        self.assertTrue(created)
        self.assertEqual(user.role, User.Role.ADVISOR)
        self.assertEqual(str(user.supabase_id), "11111111-1111-1111-1111-111111111111")
        self.assertFalse(user.has_usable_password())  # password lives in Supabase

    @patch("accounts.supabase.invite_user")
    def test_promoting_existing_supabase_user_skips_reinvite(self, mock_invite):
        from accounts.supabase import provision_advisor

        User.objects.create(
            email="student@example.com",
            supabase_id="22222222-2222-2222-2222-222222222222",
        )
        user, created = provision_advisor("student@example.com")
        mock_invite.assert_not_called()  # already has an identity
        self.assertFalse(created)
        self.assertEqual(user.role, User.Role.ADVISOR)


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


class AdvisorMessagingTests(APITestCase):
    def setUp(self):
        self.advisor = User.objects.create_user(email="adv@example.com", role=User.Role.ADVISOR)
        self.other_advisor = User.objects.create_user(email="adv2@example.com", role=User.Role.ADVISOR)
        self.premium = User.objects.create_user(email="prem@example.com", tier=User.Tier.PREMIUM)
        self.student = Student.objects.create(user=self.premium, assigned_advisor=self.advisor)

    def _send_as(self, user, url_name, *args, body="hello"):
        self.client.force_authenticate(user)
        return self.client.post(reverse(url_name, args=args), {"body": body})

    def test_premium_student_can_message_and_advisor_sees_it(self):
        resp = self._send_as(self.premium, "my_advisor_messages", body="Need help with SOP")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.advisor)
        resp = self.client.get(reverse("advisor_student_messages", args=[self.student.pk]))
        self.assertEqual(len(resp.data["messages"]), 1)
        self.assertEqual(resp.data["messages"][0]["body"], "Need help with SOP")
        self.assertFalse(resp.data["messages"][0]["mine"])  # advisor didn't send it

    def test_advisor_reply_flows_back_to_student(self):
        self._send_as(self.advisor, "advisor_student_messages", self.student.pk, body="Send your draft")
        self.client.force_authenticate(self.premium)
        resp = self.client.get(reverse("my_advisor_messages"))
        self.assertEqual(resp.data["messages"][0]["body"], "Send your draft")
        self.assertFalse(resp.data["messages"][0]["mine"])

    def test_non_premium_student_cannot_send_but_can_read(self):
        free_user = User.objects.create_user(email="free@example.com", tier=User.Tier.FREE)
        Student.objects.create(user=free_user, assigned_advisor=self.advisor)
        # Read allowed
        self.client.force_authenticate(free_user)
        self.assertEqual(self.client.get(reverse("my_advisor_messages")).status_code, 200)
        # Send blocked
        resp = self.client.post(reverse("my_advisor_messages"), {"body": "hi"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_lapsed_premium_thread_becomes_read_only(self):
        # Premium sends, then subscription lapses to full.
        self._send_as(self.premium, "my_advisor_messages", body="first")
        self.premium.tier = User.Tier.FULL
        self.premium.save(update_fields=["tier"])
        self.client.force_authenticate(self.premium)
        self.assertEqual(self.client.get(reverse("my_advisor_messages")).status_code, 200)
        resp = self.client.post(reverse("my_advisor_messages"), {"body": "again"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_advisor_cannot_message_unassigned_student(self):
        stranger = Student.objects.create(
            user=User.objects.create_user(email="stranger@example.com", tier=User.Tier.PREMIUM),
            assigned_advisor=self.other_advisor,
        )
        resp = self._send_as(self.advisor, "advisor_student_messages", stranger.pk, body="hi")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_reading_marks_the_other_partys_messages_read(self):
        from .services import unread_count_for
        from .models import AdvisorThread

        self._send_as(self.premium, "my_advisor_messages", body="unread?")
        thread = AdvisorThread.objects.get(student=self.student)
        self.assertEqual(unread_count_for(thread, self.advisor), 1)
        # Advisor opens the thread -> marked read.
        self.client.force_authenticate(self.advisor)
        self.client.get(reverse("advisor_student_messages", args=[self.student.pk]))
        self.assertEqual(unread_count_for(thread, self.advisor), 0)

    def test_student_without_advisor_gets_graceful_empty(self):
        solo = User.objects.create_user(email="solo@example.com", tier=User.Tier.PREMIUM)
        Student.objects.create(user=solo)  # no advisor assigned
        self.client.force_authenticate(solo)
        resp = self.client.get(reverse("my_advisor_messages"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["messages"], [])
        resp = self.client.post(reverse("my_advisor_messages"), {"body": "anyone?"})
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)


class VoiceNoteTests(APITestCase):
    def setUp(self):
        self.advisor = User.objects.create_user(email="adv@example.com", role=User.Role.ADVISOR)
        self.stranger = User.objects.create_user(email="x@example.com", role=User.Role.ADVISOR)
        self.premium = User.objects.create_user(email="prem@example.com", tier=User.Tier.PREMIUM)
        self.student = Student.objects.create(user=self.premium, assigned_advisor=self.advisor)

    def _voice(self):
        return SimpleUploadedFile("note.m4a", b"FAKE-AUDIO-BYTES", content_type="audio/m4a")

    def test_student_sends_voice_note_and_advisor_plays_it(self):
        self.client.force_authenticate(self.premium)
        resp = self.client.post(
            reverse("my_advisor_messages"),
            {"audio": self._voice(), "audio_duration_seconds": 12},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(resp.data["audio_url"])
        self.assertEqual(resp.data["audio_duration_seconds"], 12)
        msg_id = resp.data["id"]

        # Assigned advisor can stream it.
        self.client.force_authenticate(self.advisor)
        resp = self.client.get(reverse("advisor_message_audio", args=[msg_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(resp.streaming_content), b"FAKE-AUDIO-BYTES")

    def test_empty_message_rejected(self):
        self.client.force_authenticate(self.premium)
        resp = self.client.post(reverse("my_advisor_messages"), {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outsider_cannot_stream_voice_note(self):
        msg = post_message(
            get_thread_for_student(self.student), self.premium, audio=self._voice()
        )
        self.client.force_authenticate(self.stranger)  # an advisor, but not theirs
        resp = self.client.get(reverse("advisor_message_audio", args=[msg.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        msg.audio.delete(save=False)


class DeviceAndPushTests(APITestCase):
    def setUp(self):
        self.advisor = User.objects.create_user(email="adv@example.com", role=User.Role.ADVISOR)
        self.premium = User.objects.create_user(email="prem@example.com", tier=User.Tier.PREMIUM)
        self.student = Student.objects.create(user=self.premium, assigned_advisor=self.advisor)

    def test_register_and_unregister_device(self):
        from accounts.models import DeviceToken

        self.client.force_authenticate(self.premium)
        resp = self.client.post(
            reverse("device_register"),
            {"token": "ExponentPushToken[abc]", "platform": "android"},
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(DeviceToken.objects.filter(user=self.premium).count(), 1)
        # Idempotent re-register (same token) doesn't duplicate.
        self.client.post(reverse("device_register"), {"token": "ExponentPushToken[abc]"})
        self.assertEqual(DeviceToken.objects.filter(user=self.premium).count(), 1)

        resp = self.client.delete(
            reverse("device_register"), {"token": "ExponentPushToken[abc]"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(DeviceToken.objects.filter(user=self.premium).count(), 0)

    def test_sending_a_message_pushes_to_the_recipient(self):
        from unittest.mock import patch

        from accounts.models import DeviceToken

        # Advisor has a device registered; student sends -> advisor gets pushed.
        DeviceToken.objects.create(user=self.advisor, token="ExponentPushToken[adv]")
        self.client.force_authenticate(self.premium)
        with patch("accounts.push.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"data": [{"status": "ok"}]}
            mock_post.return_value.raise_for_status.return_value = None
            # on_commit hooks (the notify task) fire only when the txn commits.
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(reverse("my_advisor_messages"), {"body": "help!"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(mock_post.call_count, 1)
        sent = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent[0]["to"], "ExponentPushToken[adv]")
        self.assertIn("help!", sent[0]["body"])

    def test_no_devices_means_no_push_call(self):
        from unittest.mock import patch

        self.client.force_authenticate(self.premium)  # advisor has no device
        with patch("accounts.push.requests.post") as mock_post:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(reverse("my_advisor_messages"), {"body": "hi"})
        mock_post.assert_not_called()
