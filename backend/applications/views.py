from rest_framework import generics

from .models import Match
from .serializers import MatchSerializer


class MatchListView(generics.ListAPIView):
    """The student's university recommendations, best fit first."""

    serializer_class = MatchSerializer

    def get_queryset(self):
        return (
            Match.objects.filter(student__user=self.request.user)
            .select_related("program__university__profile", "program__campus")
            .order_by("-score")
        )
