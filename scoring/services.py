"""Score computation helpers shared by admin and API."""

from decimal import Decimal

from .models import ApplicationScoring, ScoringCriterion


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
        sessions = sessions.filter(status=ApplicationScoring.Status.SUBMITTED)
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
