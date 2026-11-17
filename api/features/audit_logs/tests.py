from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from api.models import AuditLog


class AuditLogListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_user(username="audit-admin")
        cls.admin.groups.add(Group.objects.create(name="admin"))
        cls.user = user_model.objects.create_user(username="audit-user")
        for index in range(3):
            AuditLog.objects.create(
                id=f"audit-{index}",
                actor=cls.user,
                action="updated",
                resource_type="application",
                resource_id=f"application-{index}",
                details={"field": "state"},
            )
        AuditLog.objects.update(created_at=timezone.now())

    def test_only_admin_group_can_list_logs(self):
        self.assertEqual(self.client.get("/api/audit-logs/").status_code, 401)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/audit-logs/").status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/api/audit-logs/").status_code, 200)

    def test_pagination_and_serialization(self):
        self.client.force_login(self.admin)
        response = self.client.get("/api/audit-logs/", {"skip": 1, "take": 1})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 3)
        self.assertEqual(len(body["data"]), 1)
        entry = body["data"][0]
        self.assertEqual(entry["id"], "audit-1")
        self.assertEqual(entry["actor_id"], self.user.id)
        self.assertEqual(entry["action"], "updated")
        self.assertEqual(entry["resource_type"], "application")
        self.assertEqual(entry["resource_id"], "application-1")
        self.assertEqual(entry["details"], {"field": "state"})
        self.assertIn("created_at", entry)

        self.assertEqual(len(self.client.get("/api/audit-logs/").json()["data"]), 3)
        self.assertEqual(
            len(self.client.get("/api/audit-logs/", {"skip": 2}).json()["data"]), 1
        )
        for params in ({"take": 0}, {"skip": 10, "take": 1}):
            self.assertEqual(self.client.get("/api/audit-logs/", params).json()["data"], [])
        for params in ({"skip": -1}, {"take": -1}, {"skip": "abc"}, {"take": "abc"}):
            self.assertEqual(self.client.get("/api/audit-logs/", params).status_code, 422)

    def test_deleted_actor_does_not_remove_logs(self):
        self.user.delete()
        self.client.force_login(self.admin)
        response = self.client.get("/api/audit-logs/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 3)
        self.assertTrue(all(entry["actor_id"] is None for entry in response.json()["data"]))
