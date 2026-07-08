from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import SimpleRateThrottle

User = get_user_model()


def _rates(**overrides):
    """Patch throttle rates on the live class attribute.

    `override_settings` can't reach DRF throttles: SimpleRateThrottle binds
    THROTTLE_RATES to the settings dict at import time.
    """
    return patch.dict(SimpleRateThrottle.THROTTLE_RATES, overrides)


class AuthTests(APITestCase):
    def test_register_and_login(self):
        resp = self.client.post(
            reverse("register"),
            {"email": "student@example.com", "password": "SafePass!2026"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "student@example.com", "password": "SafePass!2026"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_register_rejects_weak_password(self):
        resp = self.client.post(
            reverse("register"),
            {"email": "student@example.com", "password": "123"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_user_defaults_to_free_tier(self):
        user = User.objects.create_user(email="s@example.com", password="SafePass!2026")
        self.assertEqual(user.tier, User.Tier.FREE)


class MeAndLogoutTests(APITestCase):
    def test_me_requires_auth(self):
        resp = self.client.get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_bootstraps_student_route(self):
        from students.models import Student

        user = User.objects.create_user(email="s@example.com")
        self.client.force_authenticate(user)
        resp = self.client.get(reverse("me"))
        self.assertEqual(resp.data["role"], "student")
        self.assertFalse(resp.data["onboarding_complete"])

        Student.objects.create(user=user)
        resp = self.client.get(reverse("me"))
        self.assertTrue(resp.data["onboarding_complete"])

    def test_me_reports_advisor_role(self):
        user = User.objects.create_user(email="adv@example.com", role=User.Role.ADVISOR)
        self.client.force_authenticate(user)
        resp = self.client.get(reverse("me"))
        self.assertEqual(resp.data["role"], "advisor")

    def test_logout_blacklists_refresh_token(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        user = User.objects.create_user(email="s@example.com")
        refresh = RefreshToken.for_user(user)
        self.client.force_authenticate(user)
        resp = self.client.post(reverse("logout"), {"refresh": str(refresh)})
        self.assertEqual(resp.status_code, status.HTTP_205_RESET_CONTENT)
        # The blacklisted token can no longer be used to refresh.
        resp = self.client.post(reverse("token_refresh"), {"refresh": str(refresh)})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_is_advisor_permission(self):
        from rest_framework.test import APIRequestFactory

        from .permissions import IsAdvisor

        request = APIRequestFactory().get("/")
        request.user = User.objects.create_user(email="s@example.com")
        self.assertFalse(IsAdvisor().has_permission(request, None))
        request.user = User.objects.create_user(
            email="adv@example.com", role=User.Role.ADVISOR
        )
        self.assertTrue(IsAdvisor().has_permission(request, None))


class ThrottleTests(APITestCase):
    """Abuse-prone public endpoints must rate-limit. Suite-wide rates are
    relaxed in test settings; these tests dial one scope down at a time."""

    def setUp(self):
        cache.clear()  # throttle counters live in the cache

    def tearDown(self):
        cache.clear()

    @_rates(otp_request="2/hour")
    def test_otp_request_throttled_per_ip(self):
        url = reverse("otp_request")
        for _ in range(2):
            resp = self.client.post(url, {"email": "a@example.com"})
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(url, {"email": "a@example.com"})
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @_rates(otp_email="2/hour", otp_request="100/hour")
    def test_otp_request_throttled_per_inbox_across_ips(self):
        User.objects.create_user(email="victim@example.com")
        url = reverse("otp_request")
        # Same inbox from rotating IPs: the per-email throttle must still bite.
        for i in range(2):
            resp = self.client.post(
                url, {"email": "victim@example.com"}, REMOTE_ADDR=f"10.0.0.{i}"
            )
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.post(
            url, {"email": "victim@example.com"}, REMOTE_ADDR="10.0.0.99"
        )
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(len(mail.outbox), 2)  # third send never happened

    @_rates(register="1/hour")
    def test_register_throttled(self):
        url = reverse("register")
        resp = self.client.post(url, {"email": "r1@example.com", "password": "SafePass!2026"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp = self.client.post(url, {"email": "r2@example.com", "password": "SafePass!2026"})
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @_rates(onboarding="1/hour")
    def test_onboarding_throttled(self):
        url = reverse("onboarding")
        resp = self.client.post(url, {"email": "o1@example.com"})
        self.assertIn(resp.status_code, (status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST))
        resp = self.client.post(url, {"email": "o2@example.com"})
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
