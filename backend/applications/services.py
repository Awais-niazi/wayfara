"""University matching engine.

Filters active programs against the student's onboarding profile and scores
each one into a Match with a Safety / Good fit / Reach rating. Deliberately a
plain function so the heuristics are easy to iterate on and unit-test.

Runs on onboarding AND whenever a match-relevant profile field changes
(students/views.py) — a match list must never describe last month's profile.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from students.models import Student
from universities.models import Program

from .models import Match

STUDY_LEVEL_TO_DEGREE = {
    Student.StudyLevel.UNDERGRADUATE: Program.DegreeLevel.BACHELORS,
    Student.StudyLevel.MASTERS: Program.DegreeLevel.MASTERS,
}


# Approximate official concordance tables mapping each test to an IELTS overall
# band: (min raw score, IELTS band), highest first — return the band for the
# highest threshold the score clears. Approximate boundaries are fine since this
# only feeds match scoring, not any published claim.
_CONCORDANCE = {
    Student.LanguageTest.TOEFL: [
        (118, Decimal("9.0")), (115, Decimal("8.5")), (110, Decimal("8.0")),
        (102, Decimal("7.5")), (94, Decimal("7.0")), (79, Decimal("6.5")),
        (60, Decimal("6.0")), (46, Decimal("5.5")), (35, Decimal("5.0")),
        (32, Decimal("4.5")),
    ],
    Student.LanguageTest.PTE: [
        (89, Decimal("9.0")), (83, Decimal("8.5")), (79, Decimal("8.0")),
        (73, Decimal("7.5")), (65, Decimal("7.0")), (58, Decimal("6.5")),
        (50, Decimal("6.0")), (43, Decimal("5.5")), (36, Decimal("5.0")),
        (30, Decimal("4.5")),
    ],
    Student.LanguageTest.DUOLINGO: [
        (160, Decimal("8.5")), (150, Decimal("8.0")), (140, Decimal("7.5")),
        (130, Decimal("7.0")), (120, Decimal("6.5")), (115, Decimal("6.0")),
        (105, Decimal("5.5")), (95, Decimal("5.0")), (85, Decimal("4.5")),
    ],
}


def _ielts_equivalent(student):
    """The student's English level as an IELTS band, converting TOEFL/PTE/
    Duolingo via concordance. None if no usable score. Without this a TOEFL 100
    would parse as '100' and clear every IELTS requirement in the catalogue."""
    # A student who flips status back to booked/not-taken may leave a stale
    # score behind (the validator ignores it there) — don't credit it.
    if student.language_test_status in (
        Student.LanguageTestStatus.NOT_TAKEN,
        Student.LanguageTestStatus.BOOKED,
    ):
        return None
    raw = (student.language_test_score or "").strip()
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except Exception:
        return None
    # Legacy rows may have a score but no test type — read those as IELTS.
    test = student.language_test or Student.LanguageTest.IELTS
    if test == Student.LanguageTest.IELTS:
        return value
    for threshold, band in _CONCORDANCE.get(test, []):
        if value >= threshold:
            return band
    return Decimal("0")  # took a test but scored below its lowest band


# Academic strength → score points. Product decision (Awais, July 2026):
# exceptional grades must move the number DRASTICALLY — ≥95% marks or GPA ≥3.5
# pushes a well-fitting program to 100. Letters map to the closest Cambridge
# band (A* ≈ 90%+). Weak/missing grades are simply +0 — the score encourages,
# it doesn't punish a fresh profile for a data gap.
def _academic_strength_points(student):
    """Points the student's grades add to every program's score (0 if no
    usable grades). Bands: exceptional +25 / strong +15 / good +8."""
    scale, raw = student.grade_scale, (student.grades or "").strip()
    if not scale or not raw:
        return 0

    if scale == Student.GradeScale.LETTER:
        letter = raw.upper()
        if letter in ("A*", "A+"):
            return 25  # exceptional
        if letter in ("A", "A-"):
            return 15  # strong
        if letter in ("B+", "B"):
            return 8   # good
        return 0

    try:
        value = Decimal(raw)
    except Exception:
        return 0
    if scale == Student.GradeScale.PERCENTAGE:
        tiers = ((Decimal(95), 25), (Decimal(85), 15), (Decimal(75), 8))
    else:  # gpa_4
        tiers = ((Decimal("3.5"), 25), (Decimal("3.0"), 15), (Decimal("2.5"), 8))
    for threshold, points in tiers:
        if value >= threshold:
            return points
    return 0


def _score_program(student, program, ielts, academic_points):
    """Return (score 0–100, fit) for one candidate program."""
    score = Decimal(50)

    if program.min_ielts_score is not None:
        if ielts is None:
            score -= 15  # requirement exists but student has no score yet
        else:
            margin = ielts - program.min_ielts_score
            score += min(margin * 20, Decimal(20))  # up to +20 for headroom

    # Grades: same boost on every program — academic strength travels with the
    # student. Exceptional (+25) + solid language headroom is what carries a
    # well-fitting program to 100.
    score += academic_points

    if program.acceptance_rate is not None:
        score += (program.acceptance_rate - 20) / 4  # ±: selective vs open

    if student.intake and program.intake == student.intake:
        score += 10

    if program.tuition_fee_eur == 0:
        score += 5  # tuition-free is a plus for every profile

    score = max(Decimal(0), min(Decimal(100), score))

    below_language_bar = (
        program.min_ielts_score is not None and (ielts is None or ielts < program.min_ielts_score)
    )
    very_selective = program.acceptance_rate is not None and program.acceptance_rate < 10
    if below_language_bar or very_selective:
        fit = Match.Fit.REACH
    elif score >= 65:
        fit = Match.Fit.SAFETY
    else:
        fit = Match.Fit.GOOD_FIT
    return score, fit


def match_programs_for_student(student_id):
    """Regenerate matches for a student. Runs as a background task."""
    student = Student.objects.get(pk=student_id)

    programs = Program.objects.filter(is_active=True, university__is_active=True)
    # A closed application window disqualifies a program outright — recommending
    # it would be actively harmful advice. Unknown deadlines stay in (a data gap
    # is not a fact about the program).
    programs = programs.exclude(application_deadline__lt=timezone.localdate())
    if student.study_level:
        programs = programs.filter(degree_level=STUDY_LEVEL_TO_DEGREE[student.study_level])
    if student.field_of_study:
        programs = programs.filter(field_of_study__icontains=student.field_of_study)
    # Budget: blank AND 0 both mean "tuition-free only" (the validator's
    # contract). A positive budget uses lte, which also drops null-fee rows —
    # we can't promise affordability for a program whose price we don't know.
    if not student.budget_eur_per_year:
        programs = programs.filter(tuition_fee_eur=0)
    else:
        programs = programs.filter(tuition_fee_eur__lte=student.budget_eur_per_year)

    ielts = _ielts_equivalent(student)
    academic_points = _academic_strength_points(student)

    with transaction.atomic():
        Match.objects.filter(student=student).delete()
        Match.objects.bulk_create(
            Match(student=student, program=p, score=score, fit=fit)
            for p in programs.select_related("university")
            for score, fit in [_score_program(student, p, ielts, academic_points)]
        )
    return Match.objects.filter(student=student).count()


# ─── Application workspace ────────────────────────────────────────────────────

# The standard Finnish master's document set — every programme's checklist
# unless the KB team has curated a program-specific RequiredDocument list
# (universities.RequiredDocument; replacement semantics, not merge).
BASELINE_CHECKLIST = (
    # (doc_type, required, notes)
    ("transcript", True, "Complete academic transcript, in English"),
    ("degree_certificate", True, "Degree/school certificate (attested copy)"),
    ("language_certificate", True, "IELTS/TOEFL/PTE result — check the programme minimum"),
    ("passport", True, "Photo page; must be valid well past the intake"),
    ("cv", True, "Europass format is the Finnish convention"),
    ("motivation_letter", True, "Write it in the app — or upload your own"),
    ("recommendation_letter", False, "1–2 academic referees; some programmes require them"),
)

# Status transitions that are milestones worth telling the student about.
_MILESTONE_COPY = {
    "submitted": ("Application submitted 🚀", "{program} — {university}. Fingers crossed; track decisions here."),
    "offer_received": ("Offer received 🎉", "{university} offered you a place in {program}!"),
    "waitlisted": ("Waitlisted", "{university} put you on the waitlist for {program} — places do open up."),
    "rejected": ("Decision update", "{university} declined {program}. Your other applications are still live."),
    "place_confirmed": ("Study place confirmed 🇫🇮", "{program} at {university} is yours. Next stop: residence permit."),
}


def get_checklist(application, student_documents=None):
    """The document checklist for one application: the programme's curated
    RequiredDocument list if any, else the baseline — each entry matched
    against the student's uploaded documents (newest per doc_type wins).
    The motivation letter is also satisfied by in-app text."""
    from students.models import Document

    program = application.program
    curated = list(program.required_documents.all())
    if curated:
        rows = [(r.doc_type, r.required, r.notes) for r in curated]
    else:
        rows = list(BASELINE_CHECKLIST)

    if student_documents is None:
        student_documents = list(application.student.documents.all())
    newest_by_type = {}
    for doc in sorted(student_documents, key=lambda d: d.uploaded_at):
        newest_by_type[doc.doc_type] = doc

    labels = dict(Document.DocType.choices)
    checklist = []
    for doc_type, required, notes in rows:
        doc = newest_by_type.get(doc_type)
        fulfilled = doc is not None
        if not fulfilled and doc_type == Document.DocType.MOTIVATION_LETTER:
            fulfilled = bool(application.motivation_letter.strip())
        checklist.append(
            {
                "doc_type": doc_type,
                "label": labels.get(doc_type, doc_type),
                "required": required,
                "notes": notes,
                "fulfilled": fulfilled,
                "document_id": doc.pk if doc else None,
            }
        )
    return checklist


def transition_application(application, new_status):
    """Move an application along its ladder, stamping timestamps and firing
    milestone notifications through the platform spine. Returns the saved
    application; raises ValueError for a no-op transition."""
    from django.utils import timezone as tz

    from notifications.models import Notification
    from notifications.services import notify

    if new_status == application.status:
        raise ValueError("Application is already in that status.")
    if new_status == application.Status.SHORTLISTED:
        raise ValueError("An application can't go back to shortlisted.")

    application.status = new_status
    update = ["status", "updated_at"]
    now = tz.now()
    if new_status == application.Status.SUBMITTED and application.submitted_at is None:
        application.submitted_at = now
        update.append("submitted_at")
    if new_status in (
        application.Status.OFFER_RECEIVED,
        application.Status.WAITLISTED,
        application.Status.REJECTED,
    ) and application.decision_at is None:
        application.decision_at = now
        update.append("decision_at")
    application.save(update_fields=update)

    copy = _MILESTONE_COPY.get(new_status)
    if copy:
        title, body = copy
        context = {
            "program": application.program.name,
            "university": application.program.university.name,
        }
        notify(
            application.student.user,
            category=Notification.Category.APPLICATION,
            title=title.format(**context),
            body=body.format(**context),
            data={"type": "application", "application_id": application.pk},
        )
    return application
