from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .cache import catalog_key
from .models import University
from .serializers import UniversityDetailSerializer, UniversityListSerializer

# Safety-net TTL. Correctness comes from version-keyed invalidation (a write
# bumps the version, orphaning old keys); this just stops dead keys lingering.
CATALOG_TTL = 60 * 60 * 24


class UniversityListView(APIView):
    """Public discovery: every active university with its curated KB fields.

    Identical for every visitor and cached by catalog version, so it serves
    from Redis until the catalog actually changes.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        key = catalog_key("universities:list")
        data = cache.get(key)
        if data is None:
            qs = (
                University.objects.filter(is_active=True)
                .select_related("profile")
                .order_by("name")
            )
            data = UniversityListSerializer(qs, many=True).data
            cache.set(key, data, CATALOG_TTL)
        return Response(data)


class UniversityDetailView(APIView):
    """One university with its active programmes; same version-keyed cache."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        key = catalog_key(f"university:{pk}")
        data = cache.get(key)
        if data is None:
            university = get_object_or_404(
                University.objects.filter(is_active=True)
                .select_related("profile")
                .prefetch_related("programs__campus"),
                pk=pk,
            )
            data = UniversityDetailSerializer(university).data
            cache.set(key, data, CATALOG_TTL)
        return Response(data)
