"""Reporting helpers for the application processing pipeline."""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.utils import timezone

from api.features.applications.models import Application
from api.features.audit_logs.models import AuditLog
from api.features.scoring.models import ApplicationAdjudication, ApplicationScoring
from api.features.tasks.models import Task, TaskAssignment


def _application_queryset(
    date_from: date | None = None,
    date_to: date | None = None,
    status_in: list[str] | None = None,
    status_not_in: list[str] | None = None,
    search: str | None = None,
):
    qs = Application.objects.exclude(state="scoring")
    if date_from is not None:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to is not None:
        qs = qs.filter(created_at__date__lte=date_to)
    if status_in:
        qs = qs.filter(state__in=status_in)
    if status_not_in:
        qs = qs.exclude(state__in=status_not_in)
    if search:
        qs = qs.filter(
            Q(project_title__icontains=search)
            | Q(company_no__icontains=search)
            | Q(email__icontains=search)
        )
    return qs


def pipeline_summary(**filters):
    qs = _application_queryset(**filters)
    total = qs.count()
    by_state = {row["state"]: row["count"] for row in qs.values("state").annotate(count=Count("id"))}
    states_order = [
        "draft",
        "verification",
        "evaluation",
        "adjudication",
        "accepted",
        "rejected",
        "feedback",
        "submitted",
        "eligible",
    ]
    funnel = [{"state": state, "count": by_state.get(state, 0)} for state in states_order if state in by_state or True]
    return {
        "total": total,
        "by_state": by_state,
        "funnel": funnel,
    }


def status_breakdown(**filters):
    qs = _application_queryset(**filters)
    rows = qs.values("state").annotate(count=Count("id")).order_by("state")
    return [{"status": row["state"], "count": row["count"]} for row in rows]


def processing_time_summary(**filters):
    qs = _application_queryset(**filters)
    terminal = qs.filter(state__in=["accepted", "rejected"])
    elapsed = []
    for app in terminal.only("created_at", "updated_at"):
        delta = app.updated_at - app.created_at
        elapsed.append(delta.total_seconds() / 86400.0)
    average_days = (sum(elapsed) / len(elapsed)) if elapsed else 0.0
    return {
        "terminal_count": terminal.count(),
        "average_cycle_days": round(average_days, 2),
        "by_state": list(qs.values("state").annotate(count=Count("id"))),
    }


def reviewer_workload():
    rows = []
    for task in Task.objects.filter(task_type__in=[Task.Type.EVALUATION, Task.Type.ADJUDICATION]):
        for assignment in task.assignments.filter(is_active=True).select_related("employee"):
            rows.append(
                {
                    "task_id": task.id,
                    "task_type": task.task_type,
                    "application_id": task.application_id,
                    "employee_id": assignment.employee_id,
                    "username": assignment.employee.username,
                    "task_status": task.status,
                }
            )
    # Aggregate per employee.
    agg = {}
    for row in rows:
        key = row["employee_id"]
        entry = agg.setdefault(
            key,
            {
                "employee_id": key,
                "username": row["username"],
                "assigned": 0,
                "completed_tasks": 0,
            },
        )
        entry["assigned"] += 1
    # Completed evaluation scorings per scorer.
    for scorer_id, count in (
        ApplicationScoring.objects.filter(status=ApplicationScoring.Status.CONFIRMED)
        .values("scorer_id")
        .annotate(count=Count("id"))
        .values_list("scorer_id", "count")
    ):
        entry = agg.setdefault(scorer_id, {"employee_id": scorer_id, "username": "", "assigned": 0, "completed_tasks": 0})
        entry["completed_tasks"] = count
    return list(agg.values())


def scoring_summary_report(**filters):
    qs = _application_queryset(**filters)
    ids = list(qs.values_list("id", flat=True))
    adjudications = ApplicationAdjudication.objects.filter(application_id__in=ids)
    accepted = qs.filter(state="accepted").count()
    rejected = qs.filter(state="rejected").count()
    pending = qs.filter(state__in=["evaluation", "adjudication"]).count()
    scores = [a.final_score for a in adjudications if a.final_score is not None]
    avg_score = (sum(scores) / len(scores)) if scores else None
    return {
        "applications": qs.count(),
        "accepted": accepted,
        "rejected": rejected,
        "pending_review": pending,
        "adjudication_count": adjudications.count(),
        "average_final_score": (float(avg_score) if avg_score is not None else None),
    }


def dashboard_kpis(**filters):
    qs = _application_queryset(**filters)
    total = qs.count()
    submitted = qs.exclude(state="draft").count()
    accepted = qs.filter(state="accepted").count()
    rejected = qs.filter(state="rejected").count()
    conversion = (accepted / submitted * 100) if submitted else 0.0
    stalled_cutoff = timezone.now() - timedelta(days=7)
    stalled = qs.filter(
        state__in=["evaluation", "adjudication"],
        updated_at__lt=stalled_cutoff,
    ).count()
    overdue_tasks = Task.objects.filter(
        status__in=[Task.Status.PENDING, Task.Status.ASSIGNED],
        created_at__lt=stalled_cutoff,
    ).count()
    return {
        "total_applications": total,
        "submitted_applications": submitted,
        "accepted": accepted,
        "rejected": rejected,
        "conversion_rate_percent": round(conversion, 2),
        "stalled_applications": stalled,
        "overdue_tasks": overdue_tasks,
    }


def stalled_applications(days: int = 7, **filters):
    cutoff = timezone.now() - timedelta(days=days)
    qs = _application_queryset(**filters).filter(
        state__in=["evaluation", "adjudication"],
        updated_at__lt=cutoff,
    )
    return list(qs.values("id", "project_title", "state", "updated_at"))


def audit_trail(
    date_from: date | None = None,
    date_to: date | None = None,
    resource_type: str | None = None,
    limit: int = 100,
):
    qs = AuditLog.objects.all().order_by("-created_at")
    if date_from is not None:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to is not None:
        qs = qs.filter(created_at__date__lte=date_to)
    if resource_type:
        qs = qs.filter(resource_type=resource_type)
    return list(
        qs.values("id", "actor_id", "action", "resource_type", "resource_id", "created_at")[
            :limit
        ]
    )


def export_rows(**filters):
    qs = _application_queryset(**filters).order_by("-created_at")
    rows = []
    for app in qs:
        rows.append(
            {
                "id": app.id,
                "project_title": app.project_title,
                "state": app.state,
                "company_no": app.company_no,
                "loan_amount": str(app.loan_amount),
                "created_at": app.created_at.isoformat(),
                "updated_at": app.updated_at.isoformat(),
            }
        )
    return rows