"""Timeline engine: turn intake + templates into a dated, per-student plan.

Anchor dates are derived from the intake start with typical Finnish admission
rhythm (joint application in January for September intake, decisions in
spring, permits over the summer). They are deliberately generic at this stage;
once a student confirms a study place, regeneration can use the program's real
deadlines instead.
"""

from datetime import date, datetime, time, timedelta, timezone as dt_timezone

from django.db import transaction
from django.utils import timezone

from .models import Reminder, Student, Task, TaskTemplate

# Days relative to intake start for each anchor (negative = before intake).
ANCHOR_OFFSETS = {
    TaskTemplate.Anchor.APPLICATION_DEADLINE: -229,  # mid-January for a Sept intake
    TaskTemplate.Anchor.OFFER_DEADLINE: -48,         # mid-July confirmation deadline
    TaskTemplate.Anchor.VISA_SUBMISSION: -108,       # mid-May, allows 8–12 wk processing
    TaskTemplate.Anchor.ARRIVAL: -7,
    TaskTemplate.Anchor.INTAKE_START: 0,
}

REMINDER_DAYS_BEFORE = (14, 7, 3)  # per PRD §6.4
REMINDER_HOUR_UTC = 9


def intake_start_date(student):
    if not student.intake or not student.intake_year:
        return None
    month, day = (9, 1) if student.intake == Student.Intake.SEPTEMBER else (1, 8)
    return date(student.intake_year, month, day)


def generate_timeline(student_id):
    """(Re)generate the student's Tasks + Reminders from active templates.

    Completed/in-progress/skipped tasks are preserved (and their templates
    skipped); only pending tasks are regenerated. Returns tasks created.
    """
    student = Student.objects.get(pk=student_id)
    start = intake_start_date(student)
    if start is None:
        return 0

    anchors = {a: start + timedelta(days=off) for a, off in ANCHOR_OFFSETS.items()}
    now = timezone.now()

    with transaction.atomic():
        touched_template_ids = set(
            student.tasks.exclude(status=Task.Status.PENDING)
            .exclude(template=None)
            .values_list("template_id", flat=True)
        )
        student.tasks.filter(status=Task.Status.PENDING).delete()

        created = 0
        for tmpl in TaskTemplate.objects.filter(is_active=True).order_by("phase", "order"):
            if tmpl.pk in touched_template_ids:
                continue
            due = (
                anchors[tmpl.offset_anchor] + timedelta(days=tmpl.offset_days)
                if tmpl.offset_anchor
                else None
            )
            task = Task.objects.create(
                student=student,
                template=tmpl,
                phase=tmpl.phase,
                title=tmpl.title,
                description=tmpl.why_it_matters,
                due_date=due,
                order=tmpl.order,
            )
            created += 1

            if tmpl.is_critical and due is not None:
                Reminder.objects.bulk_create(
                    Reminder(
                        student=student,
                        task=task,
                        title=f"{task.title} — due in {days} days",
                        body=tmpl.why_it_matters,
                        remind_at=remind_at,
                        channel=Reminder.Channel.PUSH,
                    )
                    for days in REMINDER_DAYS_BEFORE
                    for remind_at in [
                        datetime.combine(
                            due - timedelta(days=days),
                            time(REMINDER_HOUR_UTC),
                            tzinfo=dt_timezone.utc,
                        )
                    ]
                    if remind_at > now
                )
    return created
