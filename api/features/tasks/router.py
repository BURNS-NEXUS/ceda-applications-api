from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ninja import Query, Router
from ninja.errors import HttpError

from .models import ConflictDeclaration, Task, TaskAssignment
from .permissions import can_assign_supervisor, can_supervise_tasks
from .schemas import (
    ConflictDeclarationIn,
    ConflictDeclarationOut,
    SupervisorIn,
    SupervisorOut,
    TaskAssignIn,
    TaskListOut,
    TaskOut,
)
from .filters import TaskFilters
from .services import available_employees, is_currently_absent, required_assignees

router = Router()


def _require_permission(request, permission):
    if not request.auth.has_perm(f"api.{permission}"):
        raise HttpError(403, "You do not have permission to perform this action.")


def _serialize_task(task):
    active_employee_ids = {
        assignment.employee_id
        for assignment in task.assignments.all()
        if assignment.is_active
    }
    return TaskOut(
        id=task.id,
        application_id=task.application_id,
        task_type=task.task_type,
        status=task.status,
        assignees=[
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
            for user in task.assignees.all()
            if user.pk in active_employee_ids
        ],
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _task_queryset():
    return Task.objects.select_related("application").prefetch_related(
        Prefetch(
            "assignments",
            queryset=TaskAssignment.objects.select_related("employee").filter(
                is_active=True
            ),
        ),
        "assignees",
    )


@router.get("/", response=TaskListOut)
def list_tasks(request, filters: Query[TaskFilters]):
    tasks = _task_queryset()
    if not request.auth.has_perm(f"api.{can_supervise_tasks}"):
        tasks = tasks.filter(
            assignments__employee=request.auth,
            assignments__is_active=True,
        )
    tasks = filters.apply(tasks).order_by("created_at", "id")
    total = tasks.count()
    stop = filters.skip + filters.take if filters.take is not None else None
    return {
        "total": total,
        "data": [_serialize_task(task) for task in tasks[filters.skip : stop]],
    }


@router.post(
    "/{task_id}/assignees",
    response=TaskOut,
)
@csrf_exempt
def assign_employee(request, task_id: str, payload: TaskAssignIn):
    _require_permission(request, can_supervise_tasks)
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise HttpError(404, "Task not found")
    if task.status in (Task.Status.COMPLETED, Task.Status.CANCELLED):
        raise HttpError(409, "The task is no longer active")

    User = get_user_model()
    try:
        employee = User.objects.get(pk=payload.user_id, is_active=True)
    except User.DoesNotExist:
        raise HttpError(404, "Employee not found")

    candidates = list(available_employees(task.task_type))
    minimum_candidates = 1 if task.task_type == Task.Type.ADJUDICATION else 2
    if len(candidates) < minimum_candidates:
        raise HttpError(409, "At least two available employees are required")
    if employee not in candidates or is_currently_absent(employee):
        raise HttpError(422, "Employee is absent or does not have the required role")

    with transaction.atomic():
        task = Task.objects.select_for_update().get(pk=task.pk)
        active_count = task.assignments.filter(is_active=True).count()
        if active_count >= required_assignees(task.task_type):
            raise HttpError(409, "Task already has the required number of assignees")
        if TaskAssignment.objects.filter(task=task, employee=employee).exists():
            raise HttpError(409, "Employee has already been assigned to this task")
        TaskAssignment.objects.create(task=task, employee=employee)
        task.status = (
            Task.Status.ASSIGNED
            if active_count + 1 >= required_assignees(task.task_type)
            else Task.Status.PENDING
        )
        task.save(update_fields=["status", "updated_at"])

    return _serialize_task(_task_queryset().get(pk=task.pk))


@router.post(
    "/{task_id}/conflict-declarations",
    response={201: ConflictDeclarationOut},
)
@csrf_exempt
def declare_conflict(request, task_id: str, payload: ConflictDeclarationIn):
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        raise HttpError(404, "Task not found")

    with transaction.atomic():
        task = Task.objects.select_for_update().get(pk=task.pk)
        assignment = TaskAssignment.objects.filter(
            task=task,
            employee=request.auth,
            is_active=True,
        ).first()
        if assignment is None:
            raise HttpError(403, "You are not assigned to this task")
        declaration = ConflictDeclaration.objects.create(
            task=task,
            employee=request.auth,
            declaration=payload.declaration,
            reason=payload.reason,
        )
        assignment.is_active = False
        assignment.unassigned_at = timezone.now()
        assignment.save(update_fields=["is_active", "unassigned_at", "updated_at"])
        if task.assignments.filter(is_active=True).count() < required_assignees(
            task.task_type
        ):
            task.status = Task.Status.PENDING
            task.save(update_fields=["status", "updated_at"])
    return 201, declaration


@router.get("/supervisors", response=list[SupervisorOut])
def list_supervisors(request):
    _require_permission(request, can_assign_supervisor)
    permission = Permission.objects.get(
        content_type__app_label="api",
        codename=can_supervise_tasks,
    )
    users = get_user_model().objects.filter(
        user_permissions=permission,
        is_active=True,
    ).order_by("username")
    return [
        {"user_id": user.id, "username": user.username, "email": user.email}
        for user in users
    ]


@router.post("/supervisors", response={201: SupervisorOut})
@csrf_exempt
def add_supervisor(request, payload: SupervisorIn):
    _require_permission(request, can_assign_supervisor)
    User = get_user_model()
    try:
        user = User.objects.get(pk=payload.user_id, is_active=True)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")
    permission = Permission.objects.get(
        content_type__app_label="api",
        codename=can_supervise_tasks,
    )
    user.user_permissions.add(permission)
    return 201, {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
    }


@router.delete("/supervisors/{user_id}", response=dict)
@csrf_exempt
def remove_supervisor(request, user_id: str):
    _require_permission(request, can_assign_supervisor)
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found")
    permission = Permission.objects.get(
        content_type__app_label="api",
        codename=can_supervise_tasks,
    )
    user.user_permissions.remove(permission)
    return {"success": True}
