from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from api.features.applications.models import Application
from api.features.tasks.expertise import (
    matches_expertise,
    sector_for_application,
    sector_for_text,
)
from api.features.tasks.models import Task, TaskAssignment
from api.features.tasks.services import assign_task


def create_application(owner, suffix, nature="Renewable energy and irrigation"):
    application = Application.objects.create(
        owner=owner,
        project_title=f"Solar irrigation {suffix}",
        company_no=f"CO-{suffix}",
        incorporation_date=date(2025, 1, 1),
        contact_person="Contact Person",
        telephone="71000000",
        business_nature=nature,
        business_location="Gaborone",
        loan_amount="100000.00",
        email=f"owner-{suffix}@example.com",
    )
    Application.objects.filter(pk=application.pk).update(state="evaluation")
    application.refresh_from_db()
    return application


class SectorInferenceTests(TestCase):
    def test_infers_sector_from_business_text(self):
        self.assertEqual(sector_for_text("Solar irrigation", ""), "energy")
        self.assertEqual(sector_for_text("Livestock monitoring", "Agricultural tech"), "agriculture")
        self.assertEqual(sector_for_text("General trading", ""), "general")

    def test_application_sector_uses_title_and_nature(self):
        owner = get_user_model().objects.create_user(username="owner")
        application = create_application(owner, "sector")
        self.assertEqual(sector_for_application(application), "energy")

    def test_empty_expertise_accepts_any_sector(self):
        user = get_user_model().objects.create_user(username="any-sector")
        self.assertTrue(matches_expertise(user, "energy"))
        user.expertise_sectors = ["health"]
        user.save(update_fields=["expertise_sectors"])
        self.assertFalse(matches_expertise(user, "energy"))
        self.assertTrue(matches_expertise(user, "health"))


class ExpertiseAssignmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username="owner")
        group = Group.objects.create(name="evaluator")
        cls.energy_reviewer = User.objects.create_user(username="energy-reviewer")
        cls.energy_reviewer.expertise_sectors = ["energy"]
        cls.energy_reviewer.save()
        cls.health_reviewer = User.objects.create_user(username="health-reviewer")
        cls.health_reviewer.expertise_sectors = ["health"]
        cls.health_reviewer.save()
        cls.general_reviewer = User.objects.create_user(username="general-reviewer")
        for reviewer in (cls.energy_reviewer, cls.health_reviewer, cls.general_reviewer):
            reviewer.groups.add(group)

    def test_matching_reviewer_is_assigned_first(self):
        from api.features.single_types.models import SystemSettings

        settings = SystemSettings.load()
        settings.evaluators_per_application = 1
        settings.save(update_fields=["evaluators_per_application"])

        task = Task.objects.create(
            application=create_application(self.owner, "assign"),
            task_type=Task.Type.EVALUATION,
        )
        task = assign_task(task)

        self.assertEqual(task.status, Task.Status.ASSIGNED)
        self.assertEqual(
            list(task.assignments.filter(is_active=True).values_list("employee__username", flat=True)),
            ["energy-reviewer"],
        )


class ExpertPoolEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username="owner")
        group = Group.objects.create(name="evaluator")
        permission = Permission.objects.get(
            content_type__app_label="api", codename="can_evaluate_applications"
        )
        cls.energy_reviewer = User.objects.create_user(username="energy-reviewer2")
        cls.energy_reviewer.expertise_sectors = ["energy"]
        cls.energy_reviewer.save()
        cls.energy_reviewer.groups.add(group)
        cls.energy_reviewer.user_permissions.add(permission)
        cls.health_reviewer = User.objects.create_user(username="health-reviewer2")
        cls.health_reviewer.expertise_sectors = ["health"]
        cls.health_reviewer.save()
        cls.health_reviewer.groups.add(group)
        cls.health_reviewer.user_permissions.add(permission)

        cls.application = create_application(cls.owner, "pool")
        cls.task = Task.objects.create(
            application=cls.application, task_type=Task.Type.EVALUATION
        )

    def test_pool_ranks_matching_reviewer_without_hiding_others(self):
        self.client.force_login(self.energy_reviewer)
        response = self.client.get("/api/tasks/pool")
        self.assertEqual(response.status_code, 200, response.content)
        rows = response.json()["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sector"], "energy")
        self.assertTrue(rows[0]["expertise_match"])

        self.client.force_login(self.health_reviewer)
        response = self.client.get("/api/tasks/pool")
        self.assertFalse(response.json()["data"][0]["expertise_match"])

    def test_claim_then_decline_returns_task_to_pool(self):
        self.client.force_login(self.energy_reviewer)
        claim = self.client.post(
            f"/api/tasks/{self.task.id}/claim",
            data={"reason": "energy expertise"},
            content_type="application/json",
        )
        self.assertEqual(claim.status_code, 200, claim.content)
        self.task.refresh_from_db()
        self.assertEqual(
            list(self.task.assignments.filter(is_active=True).values_list("employee__username", flat=True)),
            ["energy-reviewer2"],
        )
        self.assertEqual(self.client.get("/api/tasks/pool").json()["total"], 0)

        decline = self.client.post(
            f"/api/tasks/{self.task.id}/decline",
            data={"reason": "Conflict of interest with this applicant."},
            content_type="application/json",
        )
        self.assertEqual(decline.status_code, 200, decline.content)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.PENDING)
        self.assertEqual(self.client.get("/api/tasks/pool").json()["total"], 1)
