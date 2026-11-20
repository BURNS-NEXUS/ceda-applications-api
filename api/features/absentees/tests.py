from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from api.features.absentees.models import Absentee


def grant_permissions(user, *codenames):
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="api", codename__in=codenames
        )
    )


class AbsenteeModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="employee")

    def test_is_on_leave_when_today_in_range(self):
        absentee = Absentee.objects.create(
            user=self.user,
            leave_type=Absentee.LeaveType.VACATION,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
        )
        self.assertTrue(absentee.is_on_leave)

    def test_is_on_leave_false_when_outside_range(self):
        absentee = Absentee.objects.create(
            user=self.user,
            leave_type=Absentee.LeaveType.SICK,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=5),
        )
        self.assertFalse(absentee.is_on_leave)

    def test_open_ended_leave_is_on_leave(self):
        absentee = Absentee.objects.create(
            user=self.user,
            leave_type=Absentee.LeaveType.PERSONAL,
            start_date=date.today() - timedelta(days=1),
            end_date=None,
        )
        self.assertTrue(absentee.is_on_leave)

    def test_end_before_start_is_invalid(self):
        from django.core.exceptions import ValidationError

        absentee = Absentee(
            user=self.user,
            leave_type=Absentee.LeaveType.VACATION,
            start_date=date.today(),
            end_date=date.today() - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            absentee.full_clean()

    def test_one_absence_per_user(self):
        from django.db import IntegrityError, transaction

        Absentee.objects.create(
            user=self.user,
            leave_type=Absentee.LeaveType.VACATION,
            start_date=date.today(),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Absentee.objects.create(
                user=self.user,
                leave_type=Absentee.LeaveType.SICK,
                start_date=date.today(),
            )


class AbsenteeEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="applicant")
        cls.employee = user_model.objects.create_user(username="employee")
        cls.manager = user_model.objects.create_user(username="absence-manager")
        grant_permissions(cls.manager, "add_absentee", "delete_absentee", "view_absentee")

    def test_anonymous_users_cannot_list(self):
        self.assertEqual(self.client.get("/api/absentees").status_code, 401)

    def test_anonymous_users_cannot_add(self):
        response = self.client.post(
            "/api/absentees",
            data={"user_id": self.employee.id, "leave_type": "sick", "start_date": "2026-12-01"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_anonymous_users_cannot_remove(self):
        self.assertEqual(self.client.delete("/api/absentees/123").status_code, 401)

    def test_authenticated_user_can_list(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/absentees")
        self.assertEqual(response.status_code, 200)

    def test_add_requires_permission(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/absentees",
            data={"user_id": self.employee.id, "leave_type": "sick", "start_date": "2026-12-01"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_can_add_absentee(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            "/api/absentees",
            data={
                "user_id": self.employee.id,
                "leave_type": "sick",
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=3)),
                "reason": "Flu",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        self.assertEqual(payload["username"], self.employee.username)
        self.assertEqual(payload["leave_type"], "sick")
        self.assertTrue(payload["is_on_leave"])
        self.assertEqual(Absentee.objects.count(), 1)

    def test_adding_for_unknown_user_returns_404(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            "/api/absentees",
            data={"user_id": "does-not-exist", "leave_type": "sick", "start_date": "2026-12-01"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_adding_replaces_existing_absence(self):
        self.client.force_login(self.manager)
        self.client.post(
            "/api/absentees",
            data={"user_id": self.employee.id, "leave_type": "sick", "start_date": str(date.today())},
            content_type="application/json",
        )
        self.client.post(
            "/api/absentees",
            data={"user_id": self.employee.id, "leave_type": "vacation", "start_date": str(date.today())},
            content_type="application/json",
        )
        self.assertEqual(Absentee.objects.count(), 1)
        self.assertEqual(Absentee.objects.get(user=self.employee).leave_type, "vacation")

    def test_invalid_date_range_returns_400(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            "/api/absentees",
            data={
                "user_id": self.employee.id,
                "leave_type": "sick",
                "start_date": str(date.today()),
                "end_date": str(date.today() - timedelta(days=1)),
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_remove_requires_permission(self):
        absentee = Absentee.objects.create(
            user=self.employee, leave_type=Absentee.LeaveType.SICK, start_date=date.today()
        )
        self.client.force_login(self.user)
        response = self.client.delete(f"/api/absentees/{absentee.id}")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Absentee.objects.filter(id=absentee.id).exists())

    def test_manager_can_remove_absentee(self):
        absentee = Absentee.objects.create(
            user=self.employee, leave_type=Absentee.LeaveType.SICK, start_date=date.today()
        )
        self.client.force_login(self.manager)
        response = self.client.delete(f"/api/absentees/{absentee.id}")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["success"], True)
        self.assertFalse(Absentee.objects.filter(id=absentee.id).exists())

    def test_remove_unknown_returns_404(self):
        self.client.force_login(self.manager)
        response = self.client.delete("/api/absentees/does-not-exist")
        self.assertEqual(response.status_code, 404)
