from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from .models import SystemSettings


def grant_permissions(user, *codenames):
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="api", codename__in=codenames
        )
    )


class SystemSettingsModelTests(TestCase):
    def test_load_creates_singleton_with_defaults(self):
        settings = SystemSettings.load()

        self.assertEqual(settings.pk, 1)
        self.assertEqual(settings.site_name, "My App")
        self.assertFalse(settings.maintenance_mode)
        self.assertEqual(settings.evaluators_per_application, 2)
        self.assertEqual(SystemSettings.objects.count(), 1)

    def test_load_reuses_the_existing_row(self):
        first = SystemSettings.load()
        first.site_name = "Renamed"
        first.save()

        second = SystemSettings.load()

        self.assertEqual(second.pk, 1)
        self.assertEqual(second.site_name, "Renamed")
        self.assertEqual(SystemSettings.objects.count(), 1)

    def test_save_keeps_the_primary_key_at_one(self):
        settings = SystemSettings.load()
        settings.pk = 42
        settings.save()

        self.assertEqual(settings.pk, 1)
        self.assertEqual(SystemSettings.objects.count(), 1)
        self.assertEqual(SystemSettings.load().pk, 1)

    def test_delete_is_a_no_op(self):
        settings = SystemSettings.load()

        settings.delete()

        self.assertTrue(SystemSettings.objects.filter(pk=1).exists())


class SystemSettingsEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="applicant")
        cls.manager = user_model.objects.create_user(username="settings-manager")
        grant_permissions(cls.manager, "change_systemsettings")
        cls.superuser = user_model.objects.create_superuser(
            username="superuser", password="secret"
        )

    def test_anonymous_users_cannot_read_settings(self):
        response = self.client.get("/api/settings")

        self.assertEqual(response.status_code, 401)

    def test_anonymous_users_cannot_update_settings(self):
        response = self.client.patch(
            "/api/settings",
            data={"site_name": "Anonymous"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_any_authenticated_user_can_read_settings(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/settings")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            response.json(),
            {
                "site_name": "My App",
                "maintenance_mode": False,
                "evaluators_per_application": 2,
                "minimum_score": "0",
            },
        )
        self.assertEqual(SystemSettings.objects.count(), 1)

    def test_updating_requires_the_change_permission(self):
        self.client.force_login(self.user)

        response = self.client.patch(
            "/api/settings",
            data={"site_name": "Not allowed"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(SystemSettings.load().site_name, "My App")

    def test_other_permissions_do_not_grant_update_access(self):
        grant_permissions(self.user, "manage_document_types")
        self.client.force_login(self.user)

        response = self.client.patch(
            "/api/settings",
            data={"maintenance_mode": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_manager_can_partially_update_settings(self):
        self.client.force_login(self.manager)

        response = self.client.patch(
            "/api/settings",
            data={"maintenance_mode": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertTrue(payload["maintenance_mode"])
        self.assertEqual(payload["site_name"], "My App")
        self.assertEqual(payload["evaluators_per_application"], 2)

        response = self.client.patch(
            "/api/settings",
            data={
                "site_name": "CEDA Applications",
                "evaluators_per_application": 4,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["site_name"], "CEDA Applications")
        self.assertEqual(payload["evaluators_per_application"], 4)
        # Fields that were not sent keep their previous values.
        self.assertTrue(payload["maintenance_mode"])
        self.assertEqual(SystemSettings.objects.count(), 1)

    def test_empty_patch_returns_current_settings(self):
        self.client.force_login(self.manager)

        response = self.client.patch(
            "/api/settings",
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["site_name"], "My App")

    def test_evaluators_per_application_must_be_at_least_one(self):
        self.client.force_login(self.manager)

        response = self.client.patch(
            "/api/settings",
            data={"evaluators_per_application": 0},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(SystemSettings.load().evaluators_per_application, 2)

    def test_site_name_must_not_be_blank(self):
        self.client.force_login(self.manager)

        response = self.client.patch(
            "/api/settings",
            data={"site_name": ""},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)

    def test_site_name_length_is_validated(self):
        self.client.force_login(self.manager)

        response = self.client.patch(
            "/api/settings",
            data={"site_name": "x" * 101},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)

    def test_non_boolean_maintenance_mode_is_rejected(self):
        self.client.force_login(self.manager)

        response = self.client.patch(
            "/api/settings",
            data={"maintenance_mode": "maybe"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)

    def test_permission_works_without_staff_status_or_groups(self):
        self.assertFalse(self.manager.is_staff)
        self.assertFalse(self.manager.groups.exists())
        self.client.force_login(self.manager)

        response = self.client.patch(
            "/api/settings",
            data={"site_name": "Permission based"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["site_name"], "Permission based")

    def test_superuser_can_update_settings(self):
        self.client.force_login(self.superuser)

        response = self.client.patch(
            "/api/settings",
            data={"evaluators_per_application": 3},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["evaluators_per_application"], 3)
