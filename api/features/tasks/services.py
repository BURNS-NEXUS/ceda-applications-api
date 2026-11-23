from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone

from api.features.absentees.models import Absentee
from api.features.single_types.models import SystemSettings

from .expertise import matches_expertise, sector_for_application
from .models import Task, TaskAssignment, TaskRoundRobinState

VERIFICATION_ROLE = "verification"
EVALUATION_ROLE = "evaluator"
ADJUDICATION_ROLE = "adjudicator"
LEGACY_TASK_STATES = {
    "submitted": Task.Type.VERIFICATION,
    "screening": Task.Type.VERIFICATION,
    "in_review": Task.Type.EVALUATION,
}


def role_for_task_type(task_type):
    return {
        Task.Type.VERIFICATION: VERIFICATION_ROLE,
        Task.Type.EVALUATION: EVALUATION_ROLE,
        Task.Type.ADJUDICATION: ADJUDICATION_ROLE,
    }[task_type]


def required_assignees(task_type):
    if task_type == Task.Type.VERIFICATION:
        return 1
    if task_type == Task.Type.ADJUDICATION:
        return 1
    return SystemSettings.load().evaluators_per_application


def available_employees(task_type):
    today = timezone.localdate()
    absent_user_ids = Absentee.objects.filter(
        start_date__lte=today,
    ).filter(models.Q(end_date__gte=today) | models.Q(end_date__isnull=True))
    return (
        get_user_model()
        .objects.filter(
            is_active=True,
            groups__name=role_for_task_type(task_type),
        )
        .exclude(pk__in=absent_user_ids.values("user_id"))
        .distinct()
        .order_by("date_joined", "id")
    )


def is_assigned(task, employee):
    if task is None:
        return False
    current_task = (
        Task.objects.filter(pk=task.pk)
        .values("application__state", "task_type", "status")
        .first()
    )
    if current_task is None:
        return False
    current_state = current_task["application__state"]
    current_task_type = task_type_for_application_state(current_state)
    return (
        current_task_type == task.task_type
        and current_task["task_type"] == task.task_type
        and current_task["status"] in (Task.Status.PENDING, Task.Status.ASSIGNED)
        and TaskAssignment.objects.filter(
            task=task,
            employee=employee,
            is_active=True,
            task__application__state=current_state,
        ).exists()
    )


def task_type_for_application_state(state):
    return {
        Task.Type.VERIFICATION: Task.Type.VERIFICATION,
        Task.Type.EVALUATION: Task.Type.EVALUATION,
        "scoring": Task.Type.EVALUATION,
        Task.Type.ADJUDICATION: Task.Type.ADJUDICATION,
        **LEGACY_TASK_STATES,
    }.get(state)


@transaction.atomic
def ensure_task_for_application(application):
    application.__class__.objects.select_for_update().get(pk=application.pk)
    task_type = task_type_for_application_state(application.state)
    if task_type is None:
        return None

    Task.objects.filter(
        application=application,
        status__in=[Task.Status.PENDING, Task.Status.ASSIGNED],
    ).exclude(task_type=task_type).update(status=Task.Status.COMPLETED)

    task = Task.objects.filter(
        application=application,
        task_type=task_type,
        status__in=[Task.Status.PENDING, Task.Status.ASSIGNED],
    ).first()
    if task is None:
        task = Task.objects.create(
            application=application,
            task_type=task_type,
        )
    return assign_task(task)


@transaction.atomic
def assign_task(task):
    task = Task.objects.select_for_update().get(pk=task.pk)
    if task.status in (Task.Status.COMPLETED, Task.Status.CANCELLED):
        return task

    required = required_assignees(task.task_type)
    active_assignments = list(
        TaskAssignment.objects.select_for_update().filter(
            task=task,
            is_active=True,
        )
    )
    available_employee_ids = set(
        available_employees(task.task_type).values_list("pk", flat=True)
    )
    absent_assignments = [
        assignment
        for assignment in active_assignments
        if assignment.employee_id not in available_employee_ids
    ]
    if absent_assignments:
        now = timezone.now()
        TaskAssignment.objects.filter(
            pk__in=[assignment.pk for assignment in absent_assignments]
        ).update(
            is_active=False,
            unassigned_at=now,
            updated_at=now,
        )
        active_assignments = [
            assignment
            for assignment in active_assignments
            if assignment not in absent_assignments
        ]

    slots = required - len(active_assignments)
    if slots > 0 and task.status != Task.Status.PENDING:
        task.status = Task.Status.PENDING
        task.save(update_fields=["status", "updated_at"])
    if slots <= 0:
        task.status = Task.Status.ASSIGNED
        task.save(update_fields=["status", "updated_at"])
        return task

    candidates = list(available_employees(task.task_type))
    minimum_candidates = 1 if task.task_type == Task.Type.ADJUDICATION else 2
    if len(candidates) < minimum_candidates or len(candidates) < slots:
        return task

    previous_ids = set(
        TaskAssignment.objects.filter(task=task).values_list("employee_id", flat=True)
    )
    assigned_ids = {assignment.employee_id for assignment in active_assignments}
    candidates = [
        candidate
        for candidate in candidates
        if candidate.pk not in assigned_ids and candidate.pk not in previous_ids
    ]
    if len(candidates) < slots:
        return task

    state, _ = TaskRoundRobinState.objects.select_for_update().get_or_create(
        task_type=task.task_type
    )
    sector = (
        sector_for_application(task.application)
        if task.task_type == Task.Type.EVALUATION
        else None
    )

    # Expertise matches are considered first; the round-robin cursor spreads
    # work fairly within each tier (and across everyone for non-evaluation tasks).
    last_id = state.last_employee_id_id

    def ordered(group):
        if not group:
            return []
        start = 0
        if last_id:
            for index, candidate in enumerate(group):
                if candidate.pk == last_id:
                    start = (index + 1) % len(group)
                    break
        return [group[(start + offset) % len(group)] for offset in range(len(group))]

    if sector is None:
        ranked = ordered(candidates)
    else:
        ranked = ordered([c for c in candidates if matches_expertise(c, sector)])
        ranked += ordered([c for c in candidates if not matches_expertise(c, sector)])

    selected = ranked[:slots]
    TaskAssignment.objects.bulk_create(
        [TaskAssignment(task=task, employee=employee) for employee in selected]
    )
    state.last_employee_id = selected[-1]
    state.save(update_fields=["last_employee_id", "updated_at"])

    assignment_count = len(active_assignments) + len(selected)
    task.status = (
        Task.Status.ASSIGNED if assignment_count >= required else Task.Status.PENDING
    )
    task.save(update_fields=["status", "updated_at"])
    return task


@transaction.atomic
def retry_pending_tasks():
    assigned = 0
    for task in (
        Task.objects.select_for_update()
        .filter(status__in=[Task.Status.PENDING, Task.Status.ASSIGNED])
        .select_related("application")
    ):
        before = task.assignments.filter(is_active=True).count()
        assign_task(task)
        after = task.assignments.filter(is_active=True).count()
        assigned += max(after - before, 0)
    return assigned


def is_currently_absent(user):
    today = timezone.localdate()
    return (
        Absentee.objects.filter(
            user=user,
            start_date__lte=today,
        )
        .filter(models.Q(end_date__gte=today) | models.Q(end_date__isnull=True))
        .exists()
    )


def _active_evaluation_assignments(application):
    return TaskAssignment.objects.filter(
        task__application=application,
        task__task_type=Task.Type.EVALUATION,
        task__status__in=[Task.Status.PENDING, Task.Status.ASSIGNED],
        is_active=True,
    )


def user_can_evaluate(user, application):
    return _active_evaluation_assignments(application).filter(employee=user).exists()


def _active_adjudication_assignments(application):
    return TaskAssignment.objects.filter(
        task__application=application,
        task__task_type=Task.Type.ADJUDICATION,
        task__status__in=[Task.Status.PENDING, Task.Status.ASSIGNED],
        is_active=True,
    )


def user_can_adjudicate(user, application):
    return _active_adjudication_assignments(application).filter(employee=user).exists()


def evaluators_total(application):
    return TaskAssignment.objects.filter(
        task__application=application,
        task__task_type=Task.Type.EVALUATION,
        task__status__in=[
            Task.Status.PENDING,
            Task.Status.ASSIGNED,
            Task.Status.COMPLETED,
        ],
        is_active=True,
    ).count()


def submissions_total(application):
    from api.features.scoring.models import ApplicationScoring

    return ApplicationScoring.objects.filter(
        application=application, status=ApplicationScoring.Status.CONFIRMED
    ).count()


def complete_task(task):
    if task is None:
        return None
    task.status = Task.Status.COMPLETED
    task.save(update_fields=["status", "updated_at"])
    return task


def create_adjudication_task(application):
    task = Task.objects.filter(
        application=application,
        task_type=Task.Type.ADJUDICATION,
        status__in=[Task.Status.PENDING, Task.Status.ASSIGNED],
    ).first()
    if task is None:
        task = Task.objects.create(
            application=application, task_type=Task.Type.ADJUDICATION
        )
    return task


def assign_adjudicator(application):
    task = create_adjudication_task(application)
    return assign_task(task)
