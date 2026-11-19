from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from api.features.absentees.models import Absentee
from api.features.applications.models import Application
from api.features.single_types.models import SystemSettings
from api.features.tasks.models import (
    ConflictDeclaration,
    Task,
    TaskAssignment,
)
from api.features.tasks.permissions import can_assign_supervisor, can_supervise_tasks
from api.features.tasks.services import (
    assign_task,
    ensure_task_for_application,
    is_assigned,
)


def grant_permissions(user, *codenames):
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="api", codename__in=codenames
        )
    )


def create_application(owner, suffix):
    application = Application.objects.create(
        owner=owner,
        project_title=f"Application {suffix}",
        company_no=f"CO-{suffix}",
        incorporation_date=date(2025, 1, 1),
        contact_person="Contact Person",
        telephone="71000000",
        business_nature="Retail",
        business_location="Gaborone",
        loan_amount="100000.00",
        email=f"owner-{suffix}@example.com",
    )
    Application.objects.filter(pk=application.pk).update(state="verification")
    application.refresh_from_db()
    return application


class TaskAssignmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username="owner")
        verification = Group.objects.create(name="verification")
        evaluation = Group.objects.create(name="evaluator")
        cls.verifiers = [
            User.objects.create_user(username=f"verifier-{index}")
            for index in range(2)
        ]
        cls.evaluators = [
            User.objects.create_user(username=f"evaluator-{index}")
            for index in range(3)
        ]
        for verifier in cls.verifiers:
            verifier.groups.add(verification)
        for evaluator in cls.evaluators:
            evaluator.groups.add(evaluation)

    def test_assignment_waits_until_two_employees_are_available(self):
        self.verifiers[1].groups.clear()
        task = Task.objects.create(
            application=create_application(self.owner, "only-one"),
            task_type=Task.Type.VERIFICATION,
        )

        assign_task(task)

        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.PENDING)
        self.assertFalse(task.assignments.exists())

    def test_verification_assignment_rotates_between_employees(self):
        first = ensure_task_for_application(
            create_application(self.owner, "first")
        )
        second = ensure_task_for_application(
            create_application(self.owner, "second")
        )

        self.assertEqual(
            list(
                first.assignments.filter(is_active=True).values_list(
                    "employee_id", flat=True
                )
            ),
            [self.verifiers[0].pk],
        )
        self.assertEqual(
            list(
                second.assignments.filter(is_active=True).values_list(
                    "employee_id", flat=True
                )
            ),
            [self.verifiers[1].pk],
        )

    def test_assignment_must_match_current_application_state(self):
        application = create_application(self.owner, "state-aware")
        task = Task.objects.create(
            application=application,
            task_type=Task.Type.VERIFICATION,
            status=Task.Status.ASSIGNED,
        )
        TaskAssignment.objects.create(task=task, employee=self.verifiers[0])

        self.assertTrue(is_assigned(task, self.verifiers[0]))

        Application.objects.filter(pk=application.pk).update(state="evaluation")
        application.refresh_from_db()
        task.refresh_from_db()

        self.assertFalse(is_assigned(task, self.verifiers[0]))

    def test_inactive_or_closed_assignment_is_not_current(self):
        application = create_application(self.owner, "inactive-assignment")
        task = Task.objects.create(
            application=application,
            task_type=Task.Type.VERIFICATION,
            status=Task.Status.COMPLETED,
        )
        TaskAssignment.objects.create(task=task, employee=self.verifiers[0])

        self.assertFalse(is_assigned(task, self.verifiers[0]))

    def test_missing_task_is_not_assigned(self):
        self.assertFalse(is_assigned(None, self.verifiers[0]))

    def test_absent_employees_are_not_assigned(self):
        today = timezone.localdate()
        Absentee.objects.create(
            user=self.verifiers[0],
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=1),
        )
        extra_verifier = get_user_model().objects.create_user(
            username="verifier-third"
        )
        extra_verifier.groups.add(Group.objects.get(name="verification"))
        task = Task.objects.create(
            application=create_application(self.owner, "absent"),
            task_type=Task.Type.VERIFICATION,
        )

        assign_task(task)

        assigned = task.assignments.get(is_active=True).employee
        self.assertIn(assigned, [self.verifiers[1], extra_verifier])
        self.assertNotEqual(assigned, self.verifiers[0])

    def test_future_absence_does_not_exclude_employee(self):
        Absentee.objects.create(
            user=self.verifiers[0],
            start_date=timezone.localdate() + timedelta(days=3),
        )
        task = Task.objects.create(
            application=create_application(self.owner, "future-absence"),
            task_type=Task.Type.VERIFICATION,
        )

        assign_task(task)

        self.assertEqual(
            task.assignments.get(is_active=True).employee,
            self.verifiers[0],
        )

    def test_evaluation_respects_configured_number_of_evaluators(self):
        settings = SystemSettings.load()
        settings.evaluators_per_application = 2
        settings.save()
        application = create_application(self.owner, "evaluation")
        Task.objects.filter(application=application).update(status=Task.Status.COMPLETED)
        Application.objects.filter(pk=application.pk).update(state="evaluation")
        application.refresh_from_db()

        task = ensure_task_for_application(application)

        self.assertEqual(task.task_type, Task.Type.EVALUATION)
        self.assertEqual(task.assignments.filter(is_active=True).count(), 2)
        self.assertEqual(task.status, Task.Status.ASSIGNED)

    def test_daily_command_creates_missing_stage_tasks(self):
        application = create_application(self.owner, "command")

        call_command("assign_tasks")

        task = Task.objects.get(
            application=application,
            task_type=Task.Type.VERIFICATION,
        )
        self.assertEqual(task.assignments.filter(is_active=True).count(), 1)

    def test_daily_assignment_replaces_an_employee_who_became_absent(self):
        application = create_application(self.owner, "became-absent")
        task = Task.objects.create(
            application=application,
            task_type=Task.Type.VERIFICATION,
            status=Task.Status.ASSIGNED,
        )
        TaskAssignment.objects.create(task=task, employee=self.verifiers[0])
        Absentee.objects.create(
            user=self.verifiers[0],
            start_date=timezone.localdate(),
        )
        extra_verifier = get_user_model().objects.create_user(
            username="absence-replacement"
        )
        extra_verifier.groups.add(Group.objects.get(name="verification"))

        call_command("assign_tasks")

        self.assertFalse(
            task.assignments.filter(
                employee=self.verifiers[0],
                is_active=True,
            ).exists()
        )
        self.assertTrue(task.assignments.filter(is_active=True).exists())


class TaskEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username="task-owner")
        cls.employee = User.objects.create_user(username="task-employee")
        cls.other_employee = User.objects.create_user(username="other-employee")
        cls.supervisor = User.objects.create_user(username="supervisor")
        cls.admin = User.objects.create_user(username="task-admin")
        role = Group.objects.create(name="verification")
        cls.employee.groups.add(role)
        cls.other_employee.groups.add(role)
        grant_permissions(cls.supervisor, can_supervise_tasks)
        grant_permissions(cls.admin, can_assign_supervisor)
        cls.application = create_application(cls.owner, "endpoint")
        cls.task = Task.objects.create(
            application=cls.application,
            task_type=Task.Type.VERIFICATION,
            status=Task.Status.ASSIGNED,
        )
        TaskAssignment.objects.create(task=cls.task, employee=cls.employee)

    def setUp(self):
        self.client.force_login(self.employee)

    def test_employee_sees_only_their_assigned_tasks(self):
        response = self.client.get("/api/tasks/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["data"][0]["id"], self.task.id)

    def test_task_filters_by_type_and_assignment(self):
        response = self.client.get(
            "/api/tasks/",
            {"task_type": "verification", "assignee_id": self.employee.id},
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], 1)

    def test_task_grants_application_read_access(self):
        response = self.client.get(f"/api/applications/{self.application.id}")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["id"], self.application.id)

    def test_assigned_applications_are_only_in_explicit_task_filter(self):
        response = self.client.get("/api/applications/")
        self.assertEqual(response.json()["total"], 0)

        response = self.client.get(
            "/api/applications/",
            {"assigned_to_me": "true"},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["data"][0]["id"], self.application.id)

        self.client.force_login(self.other_employee)
        response = self.client.get(
            "/api/applications/",
            {"assigned_to_me": "true"},
        )
        self.assertEqual(response.json()["total"], 0)

    def test_unassigned_user_cannot_read_application_detail(self):
        self.client.force_login(self.other_employee)

        response = self.client.get(f"/api/applications/{self.application.id}")

        self.assertEqual(response.status_code, 404)

    def test_employee_can_unassign_themselves_with_conflict_declaration(self):
        response = self.client.post(
            f"/api/tasks/{self.task.id}/conflict-declarations",
            data={
                "declaration": "I declare that a conflict exists in this matter.",
                "reason": "The applicant is a close family member.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(
            ConflictDeclaration.objects.filter(
                task=self.task,
                employee=self.employee,
            ).exists()
        )
        assignment = TaskAssignment.objects.get(
            task=self.task,
            employee=self.employee,
        )
        self.assertFalse(assignment.is_active)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.PENDING)

    def test_supervisor_can_assign_an_eligible_employee(self):
        self.client.force_login(self.supervisor)
        response = self.client.post(
            f"/api/tasks/{self.task.id}/assignees",
            data={"user_id": self.other_employee.id},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409, response.content)

    def test_supervisor_assignment_rejects_absent_employee(self):
        self.task.assignments.update(is_active=False)
        self.task.status = Task.Status.PENDING
        self.task.save(update_fields=["status"])
        third = get_user_model().objects.create_user(username="third-employee")
        third.groups.add(Group.objects.get(name="verification"))
        Absentee.objects.create(
            user=self.other_employee,
            start_date=timezone.localdate(),
        )
        self.client.force_login(self.supervisor)

        response = self.client.post(
            f"/api/tasks/{self.task.id}/assignees",
            data={"user_id": self.other_employee.id},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422, response.content)

    def test_admin_can_assign_and_remove_supervisor_permission(self):
        candidate = get_user_model().objects.create_user(username="new-supervisor")
        self.client.force_login(self.admin)

        response = self.client.post(
            "/api/tasks/supervisors",
            data={"user_id": candidate.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(candidate.has_perm(f"api.{can_supervise_tasks}"))

        response = self.client.delete(f"/api/tasks/supervisors/{candidate.id}")
        self.assertEqual(response.status_code, 200, response.content)
        candidate = get_user_model().objects.get(pk=candidate.pk)
        self.assertFalse(candidate.has_perm(f"api.{can_supervise_tasks}"))

    def test_assigning_supervisor_requires_permission(self):
        candidate = get_user_model().objects.create_user(username="not-supervisor")

        response = self.client.post(
            "/api/tasks/supervisors",
            data={"user_id": candidate.id},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
