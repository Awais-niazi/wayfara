from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import MarkReadSerializer, NotificationSerializer

PAGE_SIZE = 30


class NotificationListView(APIView):
    """The inbox: newest first, with the unread count for the bell badge in
    the same response (one request paints the whole surface). ?before=<id>
    pages backwards through history."""

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        unread = qs.filter(read_at__isnull=True).count()
        before = request.query_params.get("before")
        if before is not None:
            if not before.isdigit():
                return Response(
                    {"before": ["Must be a notification id."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(id__lt=int(before))
        page = list(qs[: PAGE_SIZE + 1])
        has_more = len(page) > PAGE_SIZE
        return Response(
            {
                "unread_count": unread,
                "has_more": has_more,
                "results": NotificationSerializer(page[:PAGE_SIZE], many=True).data,
            }
        )


class NotificationMarkReadView(APIView):
    """Stamp read_at on the given ids (scoped to the owner) or on everything."""

    def post(self, request):
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qs = Notification.objects.filter(user=request.user, read_at__isnull=True)
        if not serializer.validated_data.get("all"):
            qs = qs.filter(id__in=serializer.validated_data["ids"])
        updated = qs.update(read_at=timezone.now())
        return Response({"marked_read": updated})
