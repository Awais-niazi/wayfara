from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Reminder, Student, Task, TaskTemplate
from .services import generate_timeline

User = get_user_model()


def make_student(**overrides):
    user = User.objects.create_user(email=overrides.pop("email", "t@example.com"))
    defaults = {"intake": "september", "intake_year": 2027, "study_level": "masters"}
    return Student.objects.create(user=user, **{**defaults, **overrides})


class TimelineEngineTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_task_templates")

    def test_seed_is_idempotent(self):
        count = TaskTemplate.objects.count()
        call_command("seed_task_templates")
        self.assertEqual(TaskTemplate.objects.count(), count)
        self.assertGreaterEqual(count, 40)

    def test_generates_dated_tasks_for_september_intake(self):
        student = make_student()
        created = generate_timeline(student.pk)
        self.assertEqual(created, TaskTemplate.objects.filter(is_active=True).count())

        # Spot-check a known rule: DVV registration = intake start (Sep 1) + 8 days
        dvv = student.tasks.get(title__startswith="Register with DVV")
        self.assertEqual(dvv.due_date, date(2027, 9, 9))
        self.assertEqual(dvv.phase, 6)

        # Tasks are ordered into phases with due dates flowing forward
        submit = student.tasks.get(title="Submit your application")
        confirm = student.tasks.get(title="Confirm your study place")
        self.assertLess(submit.due_date, confirm.due_date)
        self.assertLess(confirm.due_date, dvv.due_date)

    def test_no_intake_no_timeline(self):
        student = make_student(intake="", intake_year=None)
        self.assertEqual(generate_timeline(student.pk), 0)

    def test_book_test_task_skipped_when_score_already_given(self):
        # A student who provided a score must never be told to book the test.
        student = make_student(
            language_test_status="taken", language_test="ielts",
            language_test_score="7.0",
        )
        generate_timeline(student.pk)
        self.assertFalse(student.tasks.filter(title__startswith="Book your IELTS").exists())
        # Everyone else still gets it (status blank or booked/not_taken).
        other = make_student(email="pending@example.com", language_test_status="not_taken")
        generate_timeline(other.pk)
        self.assertTrue(other.tasks.filter(title__startswith="Book your IELTS").exists())

    def test_adding_score_in_profile_removes_pending_book_test_task(self):
        student = make_student(language_test_status="not_taken")
        generate_timeline(student.pk)
        book = student.tasks.get(title__startswith="Book your IELTS")
        self.assertEqual(book.reminders.count(), 3)  # critical → 14/7/3-day pings

        self.client.force_authenticate(student.user)
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.patch(
                reverse("profile"),
                {"language_test_status": "taken", "language_test": "ielts",
                 "language_test_score": "7.0"},
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Task AND its queued reminders are gone; the rest of the plan remains.
        self.assertFalse(student.tasks.filter(title__startswith="Book your IELTS").exists())
        self.assertFalse(Reminder.objects.filter(task=book).exists())
        self.assertTrue(student.tasks.exists())

    def test_completed_book_test_task_survives_score_arrival(self):
        # If they marked it done before entering the score, keep the history.
        student = make_student(language_test_status="booked")
        generate_timeline(student.pk)
        book = student.tasks.get(title__startswith="Book your IELTS")
        book.status = Task.Status.COMPLETED
        book.save(update_fields=["status"])

        student.language_test_status = "taken"
        student.language_test = "ielts"
        student.language_test_score = "6.5"
        student.save()
        generate_timeline(student.pk)
        self.assertTrue(
            student.tasks.filter(pk=book.pk, status=Task.Status.COMPLETED).exists()
        )

    def test_reminders_only_for_future_critical_tasks(self):
        student = make_student(intake_year=2030)  # everything far in the future
        generate_timeline(student.pk)
        critical_count = TaskTemplate.objects.filter(is_active=True, is_critical=True).count()
        self.assertEqual(Reminder.objects.filter(student=student).count(), critical_count * 3)

        past_student = make_student(email="past@example.com", intake_year=2020)
        generate_timeline(past_student.pk)
        self.assertEqual(Reminder.objects.filter(student=past_student).count(), 0)

    def test_regeneration_preserves_completed_tasks(self):
        student = make_student()
        generate_timeline(student.pk)
        done = student.tasks.filter(phase=1).first()
        done.status = Task.Status.COMPLETED
        done.save()

        generate_timeline(student.pk)
        self.assertEqual(student.tasks.filter(pk=done.pk).count(), 1)  # survived
        # Its template was not re-instantiated as a duplicate pending task
        self.assertEqual(student.tasks.filter(template=done.template).count(), 1)

    def test_tasks_api_list_filter_and_complete(self):
        student = make_student()
        generate_timeline(student.pk)
        self.client.force_authenticate(student.user)

        resp = self.client.get(reverse("tasks"), {"phase": 4})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(all(t["phase"] == 4 for t in resp.data))
        self.assertGreaterEqual(len(resp.data), 8)

        task_id = resp.data[0]["id"]
        resp = self.client.post(reverse("task_status", args=[task_id]), {"status": "completed"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "completed")
        self.assertIsNotNone(resp.data["completed_at"])

        # Another user cannot touch someone else's tasks
        other = make_student(email="other@example.com")
        self.client.force_authenticate(other.user)
        resp = self.client.post(reverse("task_status", args=[task_id]), {"status": "skipped"})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
