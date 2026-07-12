from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import HealthCheckView

# Every API endpoint — current and future — lives under this one versioned
# prefix. Bump to "api/v2/" only for a breaking change, and keep v1 alive
# alongside it until every client (mobile, web, advisor console) has moved
# off it. A guardrail test (wayfara/tests_conventions.py) fails CI if a new
# top-level route lands outside admin/, healthz, or this prefix.
API_V1 = "api/v1/"

urlpatterns = [
    path("admin/", admin.site.urls),
    # Unversioned and unauthenticated by design — see HealthCheckView.
    path("healthz", HealthCheckView.as_view(), name="health_check"),
    path(API_V1, include("accounts.urls")),
    path(API_V1, include("advisor.urls")),
    path(API_V1, include("students.urls")),
    path(API_V1, include("applications.urls")),
    path(API_V1, include("universities.urls")),
    path(f"{API_V1}auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path(f"{API_V1}auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
