from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


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
