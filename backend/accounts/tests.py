import time
import uuid

import jwt
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

TEST_SECRET = "test-supabase-jwt-secret"


def make_supabase_token(
    sub=None, email="user@example.com", *, secret=TEST_SECRET, aud="authenticated", exp_delta=3600
):
    """Mint a Supabase-shaped access token the way GoTrue would."""
    return jwt.encode(
        {
            "sub": sub or str(uuid.uuid4()),
            "email": email,
            "aud": aud,
            "exp": int(time.time()) + exp_delta,
        },
        secret,
        algorithm="HS256",
    )


@override_settings(SUPABASE_JWT_SECRET=TEST_SECRET)
class SupabaseAuthTests(APITestCase):
    """Django trusts only what it can verify against the project JWT secret,
    and provisions a local shadow user on first valid token."""

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_valid_token_provisions_local_user_just_in_time(self):
        sub = str(uuid.uuid4())
        self.assertFalse(User.objects.filter(supabase_id=sub).exists())
        self._auth(make_supabase_token(sub=sub, email="jit@example.com"))
        resp = self.client.get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "jit@example.com")
        user = User.objects.get(supabase_id=sub)
        self.assertTrue(user.email_verified)

    def test_second_request_reuses_the_same_shadow_row(self):
        sub = str(uuid.uuid4())
        for _ in range(2):
            self._auth(make_supabase_token(sub=sub, email="same@example.com"))
            self.assertEqual(self.client.get(reverse("me")).status_code, 200)
        self.assertEqual(User.objects.filter(supabase_id=sub).count(), 1)

    def test_links_email_first_row_instead_of_colliding(self):
        # An advisor pre-provisioned by email (no supabase_id yet) is linked,
        # not duplicated, on their first login.
        sub = str(uuid.uuid4())
        User.objects.create(email="adv@example.com", role=User.Role.ADVISOR)
        self._auth(make_supabase_token(sub=sub, email="adv@example.com"))
        resp = self.client.get(reverse("me"))
        self.assertEqual(resp.data["role"], "advisor")
        self.assertEqual(User.objects.filter(email="adv@example.com").count(), 1)
        self.assertEqual(str(User.objects.get(email="adv@example.com").supabase_id), sub)

    def test_no_bearer_is_401(self):
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)

    def test_bad_signature_is_rejected(self):
        self._auth(make_supabase_token(secret="not-the-secret"))
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)

    def test_expired_token_is_rejected(self):
        self._auth(make_supabase_token(exp_delta=-10))
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)

    def test_wrong_audience_is_rejected(self):
        self._auth(make_supabase_token(aud="anon"))
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)


class MeAndLogoutTests(APITestCase):
    def test_me_requires_auth(self):
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)

    def test_me_reports_username_role_and_onboarding_state(self):
        from students.models import Student

        user = User.objects.create_user(email="s@example.com", username="wanderer")
        self.client.force_authenticate(user)
        resp = self.client.get(reverse("me"))
        self.assertEqual(resp.data["username"], "wanderer")
        self.assertEqual(resp.data["role"], "student")
        self.assertFalse(resp.data["onboarding_complete"])

        Student.objects.create(user=user)
        self.assertTrue(self.client.get(reverse("me")).data["onboarding_complete"])

    def test_me_reports_advisor_role(self):
        user = User.objects.create_user(email="adv@example.com", role=User.Role.ADVISOR)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(reverse("me")).data["role"], "advisor")

    def test_logout_prunes_this_device_token(self):
        from accounts.models import DeviceToken

        user = User.objects.create_user(email="s@example.com")
        DeviceToken.objects.create(user=user, token="ExponentPushToken[gone]")
        self.client.force_authenticate(user)
        resp = self.client.post(reverse("logout"), {"device_token": "ExponentPushToken[gone]"})
        self.assertEqual(resp.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertFalse(DeviceToken.objects.filter(user=user).exists())

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


class UserModelTests(APITestCase):
    def test_new_user_defaults_to_free_tier(self):
        user = User.objects.create_user(email="s@example.com")
        self.assertEqual(user.tier, User.Tier.FREE)
