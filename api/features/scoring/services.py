"""Score computation helpers shared by admin and API."""

from decimal import Decimal

import django_fsm as fsm
from django.db import transaction
from django.utils import timezone

from api.features.applications.models import Application
from api.features.tasks import services as task_services
from api.features.tasks.models import Task

from .models import ApplicationAdjudication, ApplicationScoring, ScoringCriterion


def raw_total(scoring: ApplicationScoring) -> Decimal:
    """Sum of all criterion scores in a scoring session."""
    total = Decimal("0")
    for score in scoring.scores.all():
        total += score.score
    return total


def weighted_total(scoring: ApplicationScoring) -> Decimal:
    """Sum of score * criterion.weight across a scoring session."""
    total = Decimal("0")
    for score in scoring.scores.select_related("criterion").all():
        total += score.score * score.criterion.weight
    return total


def scoring_summary(application, include_drafts: bool = False):
    """Build the reporting summary for an application's scorings.

    Returns a dict with per-scorer totals, per-criterion means, and an
    overall weighted mean (weighted mean of per-criterion means).
    """
    sessions = application.scorings.select_related("scorer").prefetch_related(
        "scores__criterion"
    )
    if not include_drafts:
        sessions = sessions.filter(status=ApplicationScoring.Status.CONFIRMED)
    sessions = list(sessions)

    criteria = list(
        ScoringCriterion.objects.filter(is_active=True).order_by("order", "name")
    )

    scorer_rows = []
    for session in sessions:
        scorer_rows.append(
            {
                "scorer_id": session.scorer_id,
                "username": session.scorer.username,
                "status": session.status,
                "total_raw": raw_total(session),
                "total_weighted": weighted_total(session),
            }
        )

    criterion_means = []
    for criterion in criteria:
        values = []
        for session in sessions:
            matching = [s for s in session.scores.all() if s.criterion_id == criterion.id]
            if matching:
                values.append(matching[0].score)
        mean = (sum(values) / len(values)) if values else None
        criterion_means.append(
            {
                "criterion_id": criterion.id,
                "name": criterion.name,
                "mean_score": mean,
                "weight": criterion.weight,
            }
        )

    # Overall weighted mean: weighted mean of per-criterion means.
    weighted_sum = Decimal("0")
    weight_sum = Decimal("0")
    for entry in criterion_means:
        if entry["mean_score"] is not None:
            weighted_sum += entry["mean_score"] * entry["weight"]
            weight_sum += entry["weight"]
    overall = (weighted_sum / weight_sum) if weight_sum > 0 else None

    return {
        "scorers": scorer_rows,
        "criteria": criterion_means,
        "overall_weighted_mean": overall,
    }


# --- helpers re-exported from the task module for convenience ---
user_can_evaluate = task_services.user_can_evaluate
user_can_adjudicate = task_services.user_can_adjudicate
evaluators_total = task_services.evaluators_total
submissions_total = task_services.submissions_total
assign_adjudicator = task_services.assign_adjudicator
create_adjudication_task = task_services.create_adjudication_task


@transaction.atomic
def maybe_transition_to_adjudication(application):
    application = Application.objects.select_for_update().get(pk=application.pk)
    state = application.state
    if state not in ("evaluation", "scoring"):
        return application

    total_evaluators = task_services.evaluators_total(application)
    total_submissions = task_services.submissions_total(application)
    if total_evaluators <= 0 or total_submissions < total_evaluators:
        return application

    if not fsm.can_proceed(application.adjudicate):
        return application
    application.adjudicate()
    application.save()

    # Mark the evaluation task completed and create/assign the adjudication task
    # using the existing Task module.
    task_services.ensure_task_for_application(application)
    return application


def confirm_scoring(application, scorer):
    """Transition a single scoring session is handled in the router; this is a
    thin hook kept for service-level callers."""
    return maybe_transition_to_adjudication(application)


@transaction.atomic
def confirm_adjudication(application, adjudicator):
    from api.features.single_types.models import SystemSettings

    application = Application.objects.select_for_update().get(pk=application.pk)
    adjudication = ApplicationAdjudication.objects.select_for_update().get(
        application=application
    )
    if adjudication.status == ApplicationAdjudication.Status.CONFIRMED:
        raise ValueError("Adjudication is already confirmed.")
    required_ids = set(
        ScoringCriterion.objects.filter(is_active=True, is_required=True).values_list(
            "id", flat=True
        )
    )
    scored_ids = set(adjudication.scores.values_list("criterion_id", flat=True))
    if required_ids - scored_ids or adjudication.final_score is None:
        raise ValueError("All required criterion scores must be set before confirmation.")
    if not task_services.user_can_adjudicate(adjudicator, application):
        raise PermissionError("User is not assigned as adjudicator.")

    adjudication.status = ApplicationAdjudication.Status.CONFIRMED
    adjudication.confirmed_at = timezone.now()
    adjudication.save(update_fields=["status", "confirmed_at", "updated_at"])

    # Mark the adjudication task completed via the existing Task module.
    task = Task.objects.filter(
        application=application,
        task_type=Task.Type.ADJUDICATION,
        status__in=[Task.Status.PENDING, Task.Status.ASSIGNED],
    ).first()
    task_services.complete_task(task)

    settings = SystemSettings.load()
    if adjudication.final_score >= settings.minimum_score:
        if fsm.can_proceed(application.accept):
            application.accept()
            application.save()
    else:
        if fsm.can_proceed(application.reject):
            application.reject()
            application.save()
    return adjudication
