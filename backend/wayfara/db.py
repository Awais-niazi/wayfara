"""Shared model-layer helpers.

Row-level security, application tier. Every model that hangs off a Student
adopts StudentOwnedQuerySet, and views fetch through `.owned_by(request.user)`
instead of hand-writing `filter(student__user=...)` — scoping is enforced in
one audited place, not re-remembered per view. (Postgres RLS can be layered
underneath later without touching call sites.)
"""

from django.db import models


class StudentOwnedQuerySet(models.QuerySet):
    def owned_by(self, user):
        """Only rows belonging to this user's student profile."""
        return self.filter(student__user=user)


StudentOwnedManager = StudentOwnedQuerySet.as_manager
