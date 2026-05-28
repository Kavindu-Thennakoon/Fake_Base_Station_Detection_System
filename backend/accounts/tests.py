from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status


class UserProfileSignalTest(TestCase):
    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user("testuser", "test@test.com", "pass1234")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.role, "analyst")

    def test_profile_default_organization_blank(self):
        user = User.objects.create_user("testuser2", password="pass1234")
        self.assertEqual(user.profile.organization, "")


class RegisterViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_success(self):
        resp = self.client.post("/api/accounts/register/", {
            "username": "newuser",
            "email": "new@test.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", resp.data)
        self.assertEqual(resp.data["user"]["username"], "newuser")

    def test_register_password_mismatch(self):
        resp = self.client.post("/api/accounts/register/", {
            "username": "newuser",
            "email": "new@test.com",
            "password": "StrongPass123!",
            "password_confirm": "DifferentPass!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        User.objects.create_user("existing", password="pass1234")
        resp = self.client.post("/api/accounts/register/", {
            "username": "existing",
            "email": "e@test.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("admin", "admin@t.com", "admin123")

    def test_login_success(self):
        resp = self.client.post("/api/accounts/login/", {
            "username": "admin", "password": "admin123",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("token", resp.data)
        self.assertEqual(resp.data["user"]["username"], "admin")

    def test_login_wrong_password(self):
        resp = self.client.post("/api/accounts/login/", {
            "username": "admin", "password": "wrong",
        })
        self.assertIn(resp.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED])

    def test_login_nonexistent_user(self):
        resp = self.client.post("/api/accounts/login/", {
            "username": "ghost", "password": "pass",
        })
        self.assertIn(resp.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED])


class AuthenticatedViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("testauth", password="pass1234")
        resp = self.client.post("/api/accounts/login/", {
            "username": "testauth", "password": "pass1234",
        })
        self.token = resp.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")

    def test_me_endpoint(self):
        resp = self.client.get("/api/accounts/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "testauth")
        self.assertIn("profile", resp.data)

    def test_logout(self):
        resp = self.client.post("/api/accounts/logout/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp2 = self.client.get("/api/accounts/me/")
        self.assertEqual(resp2.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password(self):
        resp = self.client.post("/api/accounts/change-password/", {
            "old_password": "pass1234",
            "new_password": "NewSecure456!",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("token", resp.data)

    def test_me_unauthenticated(self):
        client2 = APIClient()
        resp = client2.get("/api/accounts/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
