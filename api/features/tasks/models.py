from django.conf import settings
from django.db import models
from django.db.models import Q

from api.base_models import BaseModel
from api.features.applications.models import Application

from .permissions import can_assign_supervisor, can_supervise_tasks


class Task(BaseModel):
    class Type(models.TextChoices):
        VERIFICATION = "verification", "Verification"
        EVALUATION = "evaluation", "Evaluation"
        ADJUDICATION = "adjudication", "Adjudication"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ASSIGNED = "assigned", "Assigned"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    task_type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="TaskAssignment",
        related_name="assigned_tasks",
        blank=True,
    )

    class Meta:
        ordering = ["created_at", "id"]  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["application", "task_type"],
                condition=Q(status__in=["pending", "assigned"]),
                name="unique_active_task_per_application_type",
            )
        ]
        permissions = [  # noqa: RUF012
            (can_supervise_tasks, "Can supervise tasks"),
            (can_assign_supervisor, "Can assign task supervisors"),
        ]

    def __str__(self):
        return f"{self.get_task_type_display()} task for {self.application_id}"


class TaskAssignment(BaseModel):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_assignments",
    )
    is_active = models.BooleanField(default=True)
    unassigned_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["created_at", "id"]  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["task", "employee"],
                name="unique_task_employee",
            )
        ]


class ConflictDeclaration(BaseModel):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="conflict_declarations",
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conflict_declarations",
    )
    declaration = models.TextField()
    reason = models.TextField()

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["task", "employee"],
                name="unique_conflict_per_task_employee",
            )
        ]


class TaskRoundRobinState(models.Model):
    task_type = models.CharField(
        primary_key=True,
        max_length=20,
        choices=Task.Type.choices,
    )
    last_employee_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Task round-robin state"
        verbose_name_plural = "Task round-robin states"
