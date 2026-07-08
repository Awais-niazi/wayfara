"""Field-risk classification for the tiered update policy.

Critical fields never auto-update — a wrong value could make a student miss a
deadline or under-fund a visa application. Anything not listed defaults to
CRITICAL (safe by default): a new scraped field must be explicitly marked LOW
before it can auto-apply.
"""

from .models import DataChange

# (app_label.Model, field) -> Risk. Only LOW entries need listing.
_LOW_RISK = {
    ("universities.University", "description"),
    ("universities.University", "logo_url"),
    ("universities.University", "website"),
    ("universities.Program", "description"),
    ("universities.Program", "entry_requirements"),
    ("universities.Program", "scholarship_notes"),
    ("universities.Program", "language"),
    ("universities.Program", "duration_years"),
}

# Everything else on these models is treated as critical (deadlines, tuition,
# IELTS minimums, Migri figures, ...). Listed here for documentation.
_KNOWN_CRITICAL = {
    ("universities.Program", "application_deadline"),
    ("universities.Program", "application_opens"),
    ("universities.Program", "start_date"),
    ("universities.Program", "tuition_fee_eur"),
    ("universities.Program", "min_ielts_score"),
    ("applications.PolicyFigure", "value"),
}


def risk_for(model_label, field):
    if (model_label, field) in _LOW_RISK:
        return DataChange.Risk.LOW
    return DataChange.Risk.CRITICAL
