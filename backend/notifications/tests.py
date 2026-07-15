"""Notification platform tests: the notify() spine, the reminder
dispatcher, broadcast targeting, the scraper hook, and the inbox API."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from students.models import Reminder, Student, Task
from universities.models import Program, University

from .models import Broadcast, Notification
from .services import dispatch_due_reminders, notify, send_broadcast

User = get_user_model()


def make_student(email, **overrides):
    user = User.objects.create_user(email=email)
    defaults = {"onboarding_completed": True}
    return Student.objects.create(user=user, **{**defaults, **overrides})


class NotifyTests(APITestCase):
    def test_notify_creates_inbox_row_and_pushes_once(self):
        from accounts.models import DeviceToken

        user = User.objects.create_user(email="n@example.com")
        DeviceToken.objects.create(user=user, token="ExponentPushToken[n]")
        with patch("accounts.push.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"data": [{"status": "ok"}]}
            mock_post.return_value.raise_for_status.return_value = None
            n = notify(
                user, category="system", title="Hello", body="World",
                data={"type": "x"},
            )
        self.assertEqual(mock_post.call_count, 1)
        sent = mock_post.call_args.kwargs["json"][0]
        self.assertEqual(sent["title"], "Hello")
        self.assertEqual(sent["data"]["notification_id"], n.pk)
        n.refresh_from_db()
        self.assertIsNotNone(n.push_sent_at)
        self.assertIsNone(n.read_at)

    def test_notify_without_devices_still_writes_the_inbox(self):
        user = User.objects.create_user(email="quiet@example.com")
        notify(user, category="news", title="Still recorded")
        self.assertEqual(user.notifications.count(), 1)


class ReminderDispatchTests(APITestCase):
    def _reminder(self, student, minutes_ago, **overrides):
        task = overrides.pop(
            "task",
            Task.objects.create(student=student, phase=4, title="Visa biometrics"),
        )
        return Reminder.objects.create(
            student=student,
            task=task,
            title="Visa biometrics — due in 3 days",
            body="Book Islamabad or Karachi now.",
            remind_at=timezone.now() - timedelta(minutes=minutes_ago),
            **overrides,
        )

    def test_due_reminder_dispatches_once(self):
        student = make_student("due@example.com")
        reminder = self._reminder(student, minutes_ago=5)

        dispatched, stale = dispatch_due_reminders()
        self.assertEqual((dispatched, stale), (1, 0))
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)
        n = student.user.notifications.get()
        self.assertEqual(n.category, Notification.Category.REMINDER)
        self.assertEqual(n.data["task_id"], reminder.task_id)

        # Second run: nothing left to claim.
        self.assertEqual(dispatch_due_reminders(), (0, 0))
        self.assertEqual(student.user.notifications.count(), 1)

    def test_stale_reminder_is_swallowed_not_pushed(self):
        student = make_student("stale@example.com")
        reminder = self._reminder(student, minutes_ago=60 * 48)  # 2 days late
        dispatched, stale = dispatch_due_reminders()
        self.assertEqual((dispatched, stale), (0, 1))
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)  # claimed, so it never fires later
        self.assertEqual(student.user.notifications.count(), 0)

    def test_future_reminders_untouched(self):
        student = make_student("future@example.com")
        reminder = self._reminder(student, minutes_ago=-60)  # due in an hour
        self.assertEqual(dispatch_due_reminders(), (0, 0))
        reminder.refresh_from_db()
        self.assertFalse(reminder.sent)


class BroadcastTests(APITestCase):
    def setUp(self):
        self.uni = University.objects.create(
            name="Aalto", institution_type="university", city="Espoo"
        )
        program = Program.objects.create(
            university=self.uni, name="CS", degree_level="masters",
            field_of_study="IT", intake="september",
        )
        self.everyone = make_student("a@example.com", intake_year=2027)
        self.later = make_student("b@example.com", intake_year=2028)
        self.matched = make_student("c@example.com", intake_year=2027)
        self.matched.matches.create(program=program, fit="good_fit", score=80)
        # Not onboarded -> never a recipient.
        make_student("ghost@example.com", onboarding_completed=False)

    def _recipients(self, **fields):
        broadcast = Broadcast.objects.create(title="T", body="B", **fields)
        send_broadcast(broadcast.pk)
        broadcast.refresh_from_db()
        emails = set(
            Notification.objects.filter(title="T").values_list("user__email", flat=True)
        )
        return broadcast, emails

    def test_all_audience(self):
        broadcast, emails = self._recipients(audience="all")
        self.assertEqual(emails, {"a@example.com", "b@example.com", "c@example.com"})
        self.assertEqual(broadcast.status, Broadcast.Status.SENT)
        self.assertEqual(broadcast.recipient_count, 3)

    def test_intake_year_audience(self):
        _, emails = self._recipients(audience="by_intake_year", intake_year=2028)
        self.assertEqual(emails, {"b@example.com"})

    def test_university_audience(self):
        _, emails = self._recipients(audience="by_university", university=self.uni)
        self.assertEqual(emails, {"c@example.com"})

    def test_sent_broadcast_cannot_resend(self):
        broadcast, _ = self._recipients(audience="all")
        before = Notification.objects.count()
        self.assertEqual(send_broadcast(broadcast.pk), 0)
        self.assertEqual(Notification.objects.count(), before)


class ScraperHookTests(APITestCase):
    def test_critical_applied_change_notifies_matched_students(self):
        from django.contrib.contenttypes.models import ContentType

        from scraping.models import DataChange, ScrapeRun, ScrapeSource

        uni = University.objects.create(
            name="LUT", institution_type="university", city="Lappeenranta"
        )
        program = Program.objects.create(
            university=uni, name="SE", degree_level="masters",
            field_of_study="IT", intake="september", tuition_fee_eur=10000,
        )
        matched = make_student("m@example.com")
        matched.matches.create(program=program, fit="good_fit", score=70)
        make_student("unrelated@example.com")

        source = ScrapeSource.objects.create(name="s", scraper_key="k", url="http://x")
        run = ScrapeRun.objects.create(source=source)
        change = DataChange.objects.create(
            run=run,
            content_type=ContentType.objects.get_for_model(Program),
            object_id=program.pk,
            field_name="tuition_fee_eur",
            old_display="10000",
            new_display="12000",
            new_value="12000",
            risk=DataChange.Risk.CRITICAL,
        )
        with self.captureOnCommitCallbacks(execute=True):
            change.apply(automatic=False)

        notes = Notification.objects.filter(category="update")
        self.assertEqual(
            set(notes.values_list("user__email", flat=True)), {"m@example.com"}
        )
        self.assertIn("LUT", notes.get().title)

    def test_low_risk_auto_apply_stays_silent(self):
        from django.contrib.contenttypes.models import ContentType

        from scraping.models import DataChange, ScrapeRun, ScrapeSource

        uni = University.objects.create(name="U", institution_type="university", city="X")
        program = Program.objects.create(
            university=uni, name="P", degree_level="masters",
            field_of_study="IT", intake="september",
        )
        make_student("s@example.com").matches.create(
            program=program, fit="good_fit", score=70
        )
        source = ScrapeSource.objects.create(name="s2", scraper_key="k", url="http://x")
        run = ScrapeRun.objects.create(source=source)
        change = DataChange.objects.create(
            run=run,
            content_type=ContentType.objects.get_for_model(Program),
            object_id=program.pk,
            field_name="description",
            new_value="new blurb",
            risk=DataChange.Risk.LOW,
        )
        with self.captureOnCommitCallbacks(execute=True):
            change.apply(automatic=True)
        self.assertEqual(Notification.objects.count(), 0)


class InboxApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="me@example.com")
        self.other = User.objects.create_user(email="other@example.com")
        self.client.force_authenticate(self.user)

    def test_list_is_scoped_and_counts_unread(self):
        notify(self.user, category="news", title="Mine", push=False)
        notify(self.other, category="news", title="Not mine", push=False)
        resp = self.client.get(reverse("notifications"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["unread_count"], 1)
        titles = [n["title"] for n in resp.data["results"]]
        self.assertEqual(titles, ["Mine"])

    def test_mark_read_by_ids_scoped_to_owner(self):
        mine = notify(self.user, category="news", title="A", push=False)
        theirs = notify(self.other, category="news", title="B", push=False)
        resp = self.client.post(
            reverse("notifications_read"), {"ids": [mine.pk, theirs.pk]}, format="json"
        )
        self.assertEqual(resp.data["marked_read"], 1)  # only mine flipped
        theirs.refresh_from_db()
        self.assertIsNone(theirs.read_at)

    def test_mark_all_read(self):
        for i in range(3):
            notify(self.user, category="news", title=f"N{i}", push=False)
        resp = self.client.post(reverse("notifications_read"), {"all": True}, format="json")
        self.assertEqual(resp.data["marked_read"], 3)
        self.assertEqual(self.client.get(reverse("notifications")).data["unread_count"], 0)

    def test_mark_read_requires_ids_or_all(self):
        resp = self.client.post(reverse("notifications_read"), {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_advisor_message_lands_in_inbox(self):
        from advisor.services import get_thread_for_student, post_message

        advisor = User.objects.create_user(email="adv@example.com", role=User.Role.ADVISOR)
        student = Student.objects.create(
            user=self.user, assigned_advisor=advisor, onboarding_completed=True
        )
        thread = get_thread_for_student(student)
        with self.captureOnCommitCallbacks(execute=True):
            post_message(thread, advisor, body="Send your transcript")
        n = self.user.notifications.get()
        self.assertEqual(n.category, Notification.Category.ADVISOR)
        self.assertIn("advisor", n.title.lower())
