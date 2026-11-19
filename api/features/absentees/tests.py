from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Absentee


def grant_permissions(user, *codenames):
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="api", codename__in=codenames
        )
    )


class AbsenteeModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="employee")

    def test_absentee_is_on_leave_during_open_ended_leave(self):
        absentee = Absentee.objects.create(
            user=self.user,
            leave_type=Absentee.LeaveType.SICK,
            start_date=timezone.localdate() - timedelta(days=1),
        )

        self.assertTrue(absentee.is_on_leave)

    def test_absentee_is_not_on_leave_after_end_date(self):
        today = timezone.localdate()
        absentee = Absentee.objects.create(
            user=self.user,
            leave_type=Absentee.LeaveType.VACATION,
            start_date=today - timedelta(days=3),
            end_date=today - timedelta(days=1),
        )

        self.assertFalse(absentee.is_on_leave)

    def test_end_date_cannot_be_before_start_date(self):
        today = timezone.localdate()
        absentee = Absentee(
            user=self.user,
            start_date=today,
            end_date=today - timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            absentee.full_clean()

    def test_user_can_only_have_one_absentee_record(self):
        Absentee.objects.create(
            user=self.user,
            start_date=timezone.localdate(),
        )
        duplicate = Absentee(
            user=self.user,
            start_date=timezone.localdate(),
        )

        with self.assertRaises(ValidationError):
            duplicate.full_clean()


class AbsenteeEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.employee = user_model.objects.create_user(username="employee")
        cls.viewer = user_model.objects.create_user(username="viewer")
        cls.manager = user_model.objects.create_user(username="manager")
        grant_permissions(cls.manager, "add_absentee", "delete_absentee")

    def setUp(self):
        self.client.force_login(self.viewer)

    def test_anonymous_users_cannot_list_absentees(self):
        self.client.logout()

        response = self.client.get("/api/absentees/")

        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_list_absentees(self):
        absentee = Absentee.objects.create(
            user=self.employee,
            leave_type=Absentee.LeaveType.SICK,
            start_date=timezone.localdate(),
            reason="Medical appointment",
        )

        response = self.client.get("/api/absentees/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["id"], absentee.id)
        self.assertEqual(response.json()[0]["user_id"], self.employee.id)
        self.assertTrue(response.json()[0]["is_on_leave"])

    def test_add_absentee_requires_permission(self):
        response = self.client.post(
            "/api/absentees/",
            data={
                "user_id": self.employee.id,
                "leave_type": "sick",
                "start_date": str(timezone.localdate()),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Absentee.objects.exists())

    def test_manager_can_add_absentee(self):
        self.client.force_login(self.manager)
        today = timezone.localdate()

        response = self.client.post(
            "/api/absentees/",
            data={
                "user_id": self.employee.id,
                "leave_type": "personal",
                "start_date": str(today),
                "end_date": str(today + timedelta(days=2)),
                "reason": "Family commitment",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        absentee = Absentee.objects.get(user=self.employee)
        self.assertEqual(response.json()["id"], absentee.id)
        self.assertEqual(absentee.leave_type, Absentee.LeaveType.PERSONAL)
        self.assertTrue(response.json()["is_on_leave"])

    def test_adding_absentee_again_updates_existing_record(self):
        self.client.force_login(self.manager)
        today = timezone.localdate()
        absentee = Absentee.objects.create(
            user=self.employee,
            leave_type=Absentee.LeaveType.VACATION,
            start_date=today - timedelta(days=10),
            end_date=today - timedelta(days=5),
        )

        response = self.client.post(
            "/api/absentees/",
            data={
                "user_id": self.employee.id,
                "leave_type": "sick",
                "start_date": str(today),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Absentee.objects.count(), 1)
        absentee.refresh_from_db()
        self.assertEqual(absentee.leave_type, Absentee.LeaveType.SICK)
        self.assertIsNone(absentee.end_date)
        self.assertTrue(response.json()["is_on_leave"])

    def test_add_absentee_rejects_unknown_user(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            "/api/absentees/",
            data={
                "user_id": "missing-user",
                "leave_type": "sick",
                "start_date": str(timezone.localdate()),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)

    def test_add_absentee_rejects_invalid_date_range(self):
        self.client.force_login(self.manager)
        today = timezone.localdate()

        response = self.client.post(
            "/api/absentees/",
            data={
                "user_id": self.employee.id,
                "leave_type": "vacation",
                "start_date": str(today),
                "end_date": str(today - timedelta(days=1)),
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Absentee.objects.exists())

    def test_remove_absentee_requires_permission(self):
        absentee = Absentee.objects.create(
            user=self.employee,
            start_date=timezone.localdate(),
        )

        response = self.client.delete(f"/api/absentees/{absentee.id}")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Absentee.objects.filter(pk=absentee.pk).exists())

    def test_manager_can_remove_absentee(self):
        self.client.force_login(self.manager)
        absentee = Absentee.objects.create(
            user=self.employee,
            start_date=timezone.localdate(),
        )

        response = self.client.delete(f"/api/absentees/{absentee.id}")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json(), {"success": True})
        self.assertFalse(Absentee.objects.filter(pk=absentee.pk).exists())

    def test_remove_absentee_returns_not_found_for_unknown_id(self):
        self.client.force_login(self.manager)

        response = self.client.delete("/api/absentees/missing")

        self.assertEqual(response.status_code, 404)
