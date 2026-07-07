from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AuthFlowTests(APITestCase):
    def test_register_login_and_fetch_profile(self):
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
        access = resp.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "student@example.com")
        self.assertEqual(resp.data["tier"], "free")
        self.assertFalse(resp.data["onboarding_completed"])

    def test_register_rejects_weak_password(self):
        resp = self.client.post(
            reverse("register"),
            {"email": "student@example.com", "password": "123"},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_requires_auth(self):
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_onboarding_profile_update(self):
        user = User.objects.create_user(email="s@example.com", password="SafePass!2026")
        self.client.force_authenticate(user)
        resp = self.client.patch(
            reverse("profile"),
            {
                "study_level": "masters",
                "field_of_study": "Computer Science",
                "intake": "september",
                "intake_year": 2027,
                "stage": "exploring",
                "onboarding_completed": True,
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.study_level, "masters")
        self.assertTrue(user.onboarding_completed)

    def test_tier_is_read_only_via_api(self):
        user = User.objects.create_user(email="s2@example.com", password="SafePass!2026")
        self.client.force_authenticate(user)
        resp = self.client.patch(reverse("profile"), {"tier": "premium"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.tier, "free")
