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


class SetPasswordTests(APITestCase):
    def test_requires_auth(self):
        resp = self.client.post(reverse("set_password"), {"password": "SafePass!2026"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sets_password_after_otp_onboarding(self):
        # Onboarding creates a passwordless account; step 3 makes it usable.
        user = User.objects.create_user(email="pw@example.com")
        self.assertFalse(user.has_usable_password())
        self.client.force_authenticate(user)

        resp = self.client.post(reverse("set_password"), {"password": "SafePass!2026"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("SafePass!2026"))

        # /me/ now reports the onboarding step as done.
        resp = self.client.get(reverse("me"))
        self.assertTrue(resp.data["has_password"])

    def test_rejects_weak_password(self):
        user = User.objects.create_user(email="weak@example.com")
        self.client.force_authenticate(user)
        resp = self.client.post(reverse("set_password"), {"password": "123"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertFalse(user.has_usable_password())


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

    @_rates(password_login="2/hour")
    def test_password_login_throttled(self):
        User.objects.create_user(email="pl@example.com", password="SafePass!2026")
        url = reverse("token_obtain_pair")
        for _ in range(2):
            self.client.post(url, {"email": "pl@example.com", "password": "wrong"})
        resp = self.client.post(url, {"email": "pl@example.com", "password": "SafePass!2026"})
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class InputHardeningTests(APITestCase):
    """Malformed and hostile input must fail with a clean 4xx, never a 500,
    and never touch data it shouldn't."""

    SQLI = "a@example.com'; DROP TABLE accounts_user;--"

    def test_non_dict_json_body_is_rejected_not_500(self):
        # A JSON array used to crash OTPEmailRateThrottle before validation ran.
        for payload in ("[1,2,3]", '"just a string"'):
            resp = self.client.post(
                reverse("otp_request"), payload, content_type="application/json"
            )
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, payload)

    def test_sql_injection_payloads_fail_validation_and_leave_db_intact(self):
        before = User.objects.count()
        for url_name in ("otp_request", "otp_verify", "onboarding", "register"):
            resp = self.client.post(
                reverse(url_name), {"email": self.SQLI, "password": "x", "code": "123456"}
            )
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, url_name)
        # Table still exists and nothing was created.
        self.assertEqual(User.objects.count(), before)

    def test_otp_code_must_be_six_digits(self):
        User.objects.create_user(email="c@example.com")
        resp = self.client.post(
            reverse("otp_verify"), {"email": "c@example.com", "code": "abcdef"}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", resp.data)

    def test_password_longer_than_20_chars_is_rejected(self):
        long_pw = "Aa1!" * 6  # 24 chars, otherwise valid
        resp = self.client.post(
            reverse("register"), {"email": "long@example.com", "password": long_pw}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(email="cap@example.com")
        self.client.force_authenticate(user)
        resp = self.client.post(reverse("set_password"), {"password": long_pw})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_email_is_rejected(self):
        huge = "a" * 250 + "@example.com"  # 262 chars > RFC's 254
        resp = self.client.post(reverse("otp_request"), {"email": huge})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordLoginTests(APITestCase):
    def test_returning_user_logs_in_with_password(self):
        User.objects.create_user(email="back@example.com", password="SafePass!2026")
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "back@example.com", "password": "SafePass!2026"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_wrong_password_is_401(self):
        User.objects.create_user(email="back2@example.com", password="SafePass!2026")
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "back2@example.com", "password": "nope-nope"},
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_passwordless_otp_account_cannot_password_login(self):
        # Onboarded but never set a password (step 3 pending) — must not
        # be able to log in with an empty/guessed password.
        User.objects.create_user(email="otp-only@example.com")  # unusable password
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "otp-only@example.com", "password": ""},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "otp-only@example.com", "password": "anything"},
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class OTPStorageTests(APITestCase):
    """The OTP code is hashed at rest and never persisted in plaintext."""

    def test_code_is_stored_hashed_not_plaintext(self):
        from accounts.models import EmailOTP

        user = User.objects.create_user(email="h@example.com")
        otp = EmailOTP.issue(user)
        plaintext = otp.plaintext_code

        stored = EmailOTP.objects.get(pk=otp.pk)
        # The DB column holds a salted hash, not the 6 digits.
        self.assertNotEqual(stored.code_hash, plaintext)
        self.assertNotIn(plaintext, stored.code_hash)
        self.assertGreater(len(stored.code_hash), 20)
        # And it still verifies against the plaintext.
        self.assertTrue(stored.check_code(plaintext))
        self.assertFalse(stored.check_code("000000"))

    def test_issue_invalidates_previous_unused_codes(self):
        from accounts.models import EmailOTP

        user = User.objects.create_user(email="h2@example.com")
        first = EmailOTP.issue(user)
        EmailOTP.issue(user)  # second issue
        first.refresh_from_db()
        self.assertTrue(first.used)  # old code can no longer be used
