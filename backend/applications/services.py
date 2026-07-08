"""University matching engine.

Filters active programs against the student's onboarding profile and scores
each one into a Match with a Safety / Good fit / Reach rating. Deliberately a
plain function so the heuristics are easy to iterate on and unit-test.
"""

from decimal import Decimal

from django.db import transaction

from students.models import Student
from universities.models import Program

from .models import Match

STUDY_LEVEL_TO_DEGREE = {
    Student.StudyLevel.UNDERGRADUATE: Program.DegreeLevel.BACHELORS,
    Student.StudyLevel.MASTERS: Program.DegreeLevel.MASTERS,
}


def _parse_ielts(raw):
    try:
        return Decimal(raw.strip())
    except Exception:
        return None


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
    if student.study_level:
        programs = programs.filter(degree_level=STUDY_LEVEL_TO_DEGREE[student.study_level])
    if student.field_of_study:
        programs = programs.filter(field_of_study__icontains=student.field_of_study)
    if student.budget_eur_per_year is None:
        programs = programs.filter(tuition_fee_eur=0)
    else:
        programs = programs.exclude(tuition_fee_eur__gt=student.budget_eur_per_year)

    ielts = _parse_ielts(student.language_test_score)

    with transaction.atomic():
        Match.objects.filter(student=student).delete()
        Match.objects.bulk_create(
            Match(student=student, program=p, score=score, fit=fit)
            for p in programs.select_related("university")
            for score, fit in [_score_program(student, p, ielts)]
        )
    return Match.objects.filter(student=student).count()
