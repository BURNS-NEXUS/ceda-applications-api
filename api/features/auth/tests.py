from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase


class MyPermissionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="applicant")
        cls.manager = user_model.objects.create_user(username="document-manager")
        cls.manager.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="api",
                codename__in=["manage_document_types", "review_application_document"],
            )
        )
        cls.superuser = user_model.objects.create_superuser(
            username="superuser", password="secret"
        )

    def test_requires_authentication(self):
        response = self.client.get("/api/me/permissions")
        self.assertEqual(response.status_code, 401)

    def test_returns_granted_permissions(self):
        self.client.force_login(self.manager)

        response = self.client.get("/api/me/permissions")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["user_id"], self.manager.id)
        self.assertEqual(payload["username"], self.manager.username)
        self.assertFalse(payload["is_superuser"])
        self.assertEqual(
            set(payload["permissions"]),
            {
                "api.manage_document_types",
                "api.review_application_document",
            },
        )

    def test_user_without_permissions_gets_empty_list(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/me/permissions")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["permissions"], [])

    def test_superuser_has_all_permissions(self):
        self.client.force_login(self.superuser)

        response = self.client.get("/api/me/permissions")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertTrue(payload["is_superuser"])
        self.assertIn("api.manage_document_types", payload["permissions"])
        self.assertIn("api.review_application_document", payload["permissions"])


class UpdateMeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="profile@example.com",
            email="profile@example.com",
            first_name="Old",
            last_name="Name",
        )
        cls.other = User.objects.create_user(
            username="taken@example.com", email="taken@example.com"
        )

    def test_requires_authentication(self):
        response = self.client.patch(
            "/api/me", data={"first_name": "New"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_updates_name_and_email(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            "/api/me",
            data={
                "first_name": "New",
                "last_name": "Person",
                "email": "new@example.com",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "New")
        self.assertEqual(self.user.last_name, "Person")
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(self.user.username, "new@example.com")
        self.assertEqual(response.json()["first_name"], "New")

    def test_rejects_duplicate_email(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            "/api/me",
            data={"email": "taken@example.com"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)

    def test_partial_update_keeps_other_fields(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            "/api/me", data={"first_name": "Only"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Only")
        self.assertEqual(self.user.email, "profile@example.com")
