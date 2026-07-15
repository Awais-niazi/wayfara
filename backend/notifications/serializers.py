from rest_framework import serializers

from wayfara.serializers import StrictModelSerializer, StrictSerializer

from .models import Notification


class NotificationSerializer(StrictModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "category", "title", "body", "data", "created_at", "read_at"]


class MarkReadSerializer(StrictSerializer):
    """Mark specific notifications read, or everything at once."""

    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        max_length=200,  # bound attacker-controlled list size
    )
    all = serializers.BooleanField(required=False, default=False)

    def validate(self, data):
        if not data.get("all") and not data.get("ids"):
            raise serializers.ValidationError("Provide ids or all=true.")
        return data
