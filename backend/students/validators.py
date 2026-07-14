"""Semantic validation for the academic profile fields.

Format/length hardening lives in the serializers already; this is the layer
that rejects values that are the right *shape* but nonsense in context — an
IELTS score of 11, a GPA of 7.2 on a 4.0 scale, a €30 annual budget. Shared by
the onboarding form and the profile editor so both enforce the same rules.

Every check raises a field-keyed DRF ValidationError; callers collect them so
the API returns all problems at once, not one at a time.
"""

import re
from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models import Student

# ── Language tests ───────────────────────────────────────────────────────────
# (min, max, half_steps): half_steps=True means only .0/.5 allowed (IELTS);
# otherwise the score must be a whole number.
LANGUAGE_TEST_RANGES = {
    Student.LanguageTest.IELTS: (Decimal("0"), Decimal("9"), True),
    Student.LanguageTest.TOEFL: (Decimal("0"), Decimal("120"), False),
    Student.LanguageTest.PTE: (Decimal("10"), Decimal("90"), False),
    Student.LanguageTest.DUOLINGO: (Decimal("10"), Decimal("160"), False),
}

# ── Grades ───────────────────────────────────────────────────────────────────
GPA_MIN, GPA_MAX = Decimal("0.5"), Decimal("4")
PERCENTAGE_MIN, PERCENTAGE_MAX = 0, 100
# Single O/A-Level style grade: A–E with an optional *, + or - (A*, B+, C-).
LETTER_GRADE_RE = re.compile(r"^[A-E][*+\-]?$")

# ── Budget ───────────────────────────────────────────────────────────────────
# Blank or 0 = "tuition-free programmes only" (matching already treats it so);
# any real positive budget must be plausible for a year of study.
BUDGET_MIN, BUDGET_MAX = 1000, 100000


def _to_decimal(raw):
    try:
        return Decimal(str(raw).strip())
    except (InvalidOperation, AttributeError, ValueError):
        return None


def check_grades(grade_scale, grades, errors):
    grades = (grades or "").strip()
    if not grades:
        return  # grades are optional
    if not grade_scale:
        errors["grade_scale"] = ["Select which scale your grade is on."]
        return

    if grade_scale == Student.GradeScale.GPA_4:
        val = _to_decimal(grades)
        if val is None or not (GPA_MIN <= val <= GPA_MAX):
            errors["grades"] = [f"GPA must be between {GPA_MIN} and {GPA_MAX}."]
    elif grade_scale == Student.GradeScale.PERCENTAGE:
        val = _to_decimal(grades)
        if val is None or val != val.to_integral_value() or not (
            PERCENTAGE_MIN <= val <= PERCENTAGE_MAX
        ):
            errors["grades"] = [
                f"Percentage must be a whole number from {PERCENTAGE_MIN} to {PERCENTAGE_MAX}."
            ]
    elif grade_scale == Student.GradeScale.LETTER:
        if not LETTER_GRADE_RE.match(grades.upper()):
            errors["grades"] = ["Enter a single grade A–E, optionally with *, + or - (e.g. A*, B+, C)."]


def check_language(status, test, score, errors):
    if status != Student.LanguageTestStatus.TAKEN:
        return  # a score only matters once the test is taken
    if not test:
        errors["language_test"] = ["Select which English test you took."]
        return
    score = (score or "").strip()
    if not score:
        errors["language_test_score"] = ["Enter your test score."]
        return

    lo, hi, half_steps = LANGUAGE_TEST_RANGES[test]
    val = _to_decimal(score)
    label = Student.LanguageTest(test).label
    if val is None or not (lo <= val <= hi):
        errors["language_test_score"] = [f"{label} score must be between {lo} and {hi}."]
        return
    if half_steps:
        if (val * 2) != (val * 2).to_integral_value():
            errors["language_test_score"] = [f"{label} scores go in half-point steps (e.g. 6.5, 7.0)."]
    elif val != val.to_integral_value():
        errors["language_test_score"] = [f"{label} score must be a whole number."]


def check_budget(budget, errors):
    if budget in (None, 0):
        return  # tuition-free intent
    if not (BUDGET_MIN <= budget <= BUDGET_MAX):
        errors["budget_eur_per_year"] = [
            f"Enter a realistic annual budget (€{BUDGET_MIN:,}–€{BUDGET_MAX:,}), "
            "or leave it blank for tuition-free programmes only."
        ]


def validate_academic(values):
    """Run every academic check over an effective field dict and raise once
    with all problems. `values` is a Mapping (serializer attrs, or attrs merged
    over the instance for a partial update)."""
    errors = {}
    check_grades(values.get("grade_scale"), values.get("grades"), errors)
    check_language(
        values.get("language_test_status"),
        values.get("language_test"),
        values.get("language_test_score"),
        errors,
    )
    check_budget(values.get("budget_eur_per_year"), errors)
    if errors:
        raise serializers.ValidationError(errors)
