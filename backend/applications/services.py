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


def _score_program(student, program, ielts):
    """Return (score 0–100, fit) for one candidate program."""
    score = Decimal(50)

    if program.min_ielts_score is not None:
        if ielts is None:
            score -= 15  # requirement exists but student has no score yet
        else:
            margin = ielts - program.min_ielts_score
            score += min(margin * 20, Decimal(20))  # up to +20 for headroom

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

    with transaction.atomic():
        Match.objects.filter(student=student).delete()
        Match.objects.bulk_create(
            Match(student=student, program=p, score=score, fit=fit)
            for p in programs.select_related("university")
            for score, fit in [_score_program(student, p, ielts)]
        )
    return Match.objects.filter(student=student).count()
