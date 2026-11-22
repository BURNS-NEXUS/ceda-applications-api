from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from api.features.applications.models import Application
from .models import Clarification


class ApplicationReadTests(TestCase):
    def test_customer_detail_and_private_clarifications(self):
        user = get_user_model().objects.create_user(username="reader")
        other = get_user_model().objects.create_user(username="other")
        for owner in (user, other):
            application = Application.objects.create(
                owner=owner, project_title="Test", incorporation_date="2026-01-01",
                loan_amount=1, application_type="individual",
            )
            Clarification.objects.create(application=application, created_by=other, reason="Confirm title")
        own = Application.objects.get(owner=user)
        self.client.force_login(user)
        detail = self.client.get(f"/api/applications/{own.pk}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["application_type"], "individual")
        response = self.client.get("/api/clarifications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["application_id"] for r in response.json()["data"]], [own.pk])
        Application.objects.filter(owner=other).update(application_type="")
        user.user_permissions.add(Permission.objects.get(codename="can_view_all_applications"))
        registry = self.client.get("/api/applications/")
        self.assertEqual(registry.status_code, 200)
        self.assertEqual(registry.json()["total"], 2)
