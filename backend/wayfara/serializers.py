"""Strict base serializers every Wayfara API serializer must inherit from.

Firm rule (enforced by wayfara/tests_conventions.py, not just this docstring):
every serializer in this codebase — current and future — extends
StrictSerializer or StrictModelSerializer instead of DRF's plain
Serializer/ModelSerializer.

DRF's default behavior silently discards any request key that isn't a
declared field. That's convenient but means a typo, a stale client field, or
a mass-assignment probe against an undeclared field vanishes without a trace
instead of failing loudly. An endpoint is designed to take specific data;
anything else should be rejected, not swallowed.

This does NOT change how declared-but-read-only fields behave: DRF already
ignores those safely (they're never written), and that's the correct,
intentional behavior for round-tripping clients that PATCH back a full
object. The strict layer only targets keys the serializer doesn't recognize
at all.
"""

from collections.abc import Mapping

from rest_framework import serializers


class _RejectUnknownFieldsMixin:
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {
                        field: ["This field is not accepted by this endpoint."]
                        for field in unknown
                    }
                )
        return super().to_internal_value(data)


class StrictSerializer(_RejectUnknownFieldsMixin, serializers.Serializer):
    pass


class StrictModelSerializer(_RejectUnknownFieldsMixin, serializers.ModelSerializer):
    pass
