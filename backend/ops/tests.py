"""Observability tests: heartbeats, deep health, canaries, push receipts."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import DeviceToken
from applications.models import Match
from notifications.models import Notification
from students.models import Student
from universities.models import Program, University

from .models import Heartbeat, PushTicket
from .services import check_push_receipts, record_push_tickets, run_canaries

User = get_user_model()


class HeartbeatTests(TestCase):
    def test_beat_and_fail_upsert_one_row(self):
        Heartbeat.beat("reminder-dispatcher", {"dispatched": 3})
        Heartbeat.fail("reminder-dispatcher", RuntimeError("boom"))
        Heartbeat.beat("reminder-dispatcher")
        row = Heartbeat.objects.get(name="reminder-dispatcher")
        self.assertEqual(Heartbeat.objects.count(), 1)
        self.assertIsNotNone(row.last_ok)
        self.assertIn("boom", row.last_error_message)


class DeepHealthTests(TestCase):
    def test_healthy_in_dev_returns_200_with_check_report(self):
        resp = self.client.get(reverse("health_deep"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["checks"]["db"], "ok")
        # Eager mode (dev/tests): no beat process, so staleness must not fail.
        self.assertIn("skipped", data["checks"]["heartbeats"]["status"])

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    def test_stale_heartbeats_degrade_to_503(self):
        # No pulses ever recorded + non-eager mode → the dead-man fires.
        with patch("ops.services._check_broker", return_value="ok"):
            resp = self.client.get(reverse("health_deep"))
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["status"], "degraded")


class CanaryTests(TestCase):
    def setUp(self):
        self.uni = University.objects.create(
            name="Aalto", institution_type="university", city="Espoo"
        )
        self.program = Program.objects.create(
            university=self.uni, name="CS", degree_level="masters",
            field_of_study="IT", intake="september",
        )

    def _student(self, email, budget, minutes_ago=60):
        user = User.objects.create_user(email=email)
        student = Student.objects.create(
            user=user, onboarding_completed=True, budget_eur_per_year=budget
        )
        Student.objects.filter(pk=student.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes_ago)
        )
        return student

    def test_budgeted_student_with_zero_matches_is_flagged(self):
        self._student("starved@example.com", budget=15000)
        findings = run_canaries()
        self.assertTrue(any("ZERO matches" in f for f in findings))

    def test_blank_budget_zero_matches_is_by_design_not_flagged(self):
        self._student("frugal@example.com", budget=None)
        findings = run_canaries()
        self.assertFalse(any("ZERO matches" in f for f in findings))

    def test_matched_student_not_flagged(self):
        s = self._student("fine@example.com", budget=15000)
        Match.objects.create(student=s, program=self.program, fit="good_fit", score=70)
        findings = run_canaries()
        self.assertFalse(any("ZERO matches" in f for f in findings))

    def test_unpushed_notification_for_device_user_is_flagged(self):
        user = User.objects.create_user(email="device@example.com")
        DeviceToken.objects.create(user=user, token="ExponentPushToken[x]")
        n = Notification.objects.create(user=user, category="reminder", title="t")
        Notification.objects.filter(pk=n.pk).update(
            created_at=timezone.now() - timedelta(minutes=30)
        )
        findings = run_canaries()
        self.assertTrue(any("never pushed" in f for f in findings))

    def test_orphaned_match_on_inactive_program_is_flagged(self):
        s = self._student("orphan@example.com", budget=None)
        Match.objects.create(student=s, program=self.program, fit="good_fit", score=70)
        Program.objects.filter(pk=self.program.pk).update(is_active=False)
        findings = run_canaries()
        self.assertTrue(any("INACTIVE programmes" in f for f in findings))


class PushReceiptTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="push@example.com")
        self.token = DeviceToken.objects.create(
            user=self.user, token="ExponentPushToken[abc]"
        )

    def _ticket(self, ticket_id="t-1", minutes_old=30):
        t = PushTicket.objects.create(ticket_id=ticket_id, token=self.token.token)
        PushTicket.objects.filter(pk=t.pk).update(
            created_at=timezone.now() - timedelta(minutes=minutes_old)
        )
        return t

    def test_record_push_tickets_keeps_only_ok_tickets(self):
        record_push_tickets(
            [{"status": "ok", "id": "aa"}, {"status": "error", "id": "bb"}],
            ["tok1", "tok2"],
        )
        self.assertEqual(
            list(PushTicket.objects.values_list("ticket_id", flat=True)), ["aa"]
        )

    @patch("ops.services.requests.post")
    def test_device_not_registered_receipt_prunes_token(self, post):
        self._ticket()
        post.return_value.json.return_value = {
            "data": {"t-1": {"status": "error", "details": {"error": "DeviceNotRegistered"}}}
        }
        post.return_value.raise_for_status.return_value = None
        counters = check_push_receipts()
        self.assertEqual(counters["pruned"], 1)
        self.assertFalse(DeviceToken.objects.filter(token=self.token.token).exists())
        self.assertTrue(PushTicket.objects.get(ticket_id="t-1").checked)

    @patch("ops.services.requests.post")
    def test_delivered_receipt_counts_and_marks_checked(self, post):
        self._ticket()
        post.return_value.json.return_value = {"data": {"t-1": {"status": "ok"}}}
        post.return_value.raise_for_status.return_value = None
        counters = check_push_receipts()
        self.assertEqual(counters["delivered"], 1)
        self.assertTrue(DeviceToken.objects.filter(token=self.token.token).exists())

    def test_young_tickets_wait_for_their_receipt(self):
        self._ticket(minutes_old=5)  # under the 20-minute cutoff
        counters = check_push_receipts()
        self.assertEqual(counters["checked"], 0)
        self.assertFalse(PushTicket.objects.get(ticket_id="t-1").checked)
