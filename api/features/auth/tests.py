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
