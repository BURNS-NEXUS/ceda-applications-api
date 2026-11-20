from decimal import Decimal
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ninja import Query, Router
from ninja.errors import HttpError

from api.features.applications.models import Application
from django.contrib.auth import get_user_model

from .models import ApplicationScore, ApplicationScoring, ScoringCriterion
from .schemas import (
    ApplicationScoreIn,
    ApplicationScoreOut,
    ApplicationScoringOut,
    ApplicationScoringPatch,
    ApplicationScoringSummary,
    ApplicationScoringUpsert,
    CriterionMeanOut,
    ScorerOut,
    ScorerTotalOut,
    ScoringCriterionIn,
    ScoringCriterionOut,
)
from .services import raw_total, scoring_summary, weighted_total

router = Router()

PERM_MANAGE_CRITERIA = "scoring.manage_scoring_criteria"
PERM_VIEW_CRITERIA = "scoring.view_scoringcriterion"
PERM_SCORE_APPLICATION = "scoring.score_application"
PERM_VIEW_ALL_SCORES = "scoring.view_all_scores"
PERM_FINALIZE_SCORING = "scoring.finalize_scoring"


def _require_perm(request, permission):
    if not request.auth.has_perm(permission):
        raise HttpError(403, "You do not have permission to perform this action.")


def _has_perm(request, permission):
    return bool(request.auth and request.auth.has_perm(permission))


def _raise_validation_error(error):
    if hasattr(error, "message_dict"):
        messages = [
            message
            for field_messages in error.message_dict.values()
            for message in field_messages
        ]
    else:
        messages = list(error.messages)
    raise HttpError(400, " ".join(messages) or "Invalid data.")


def _get_application(application_id):
    try:
        return Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        raise HttpError(404, "Application not found")


def _criterion_out(criterion):
    return ScoringCriterionOut(
        id=criterion.id,
        name=criterion.name,
        description=criterion.description,
        weight=criterion.weight,
        max_score=criterion.max_score,
        score_type=criterion.score_type,
        is_required=criterion.is_required,
        is_active=criterion.is_active,
        order=criterion.order,
    )


def _score_out(score):
    return ApplicationScoreOut(
        id=score.id,
        criterion_id=score.criterion_id,
        criterion_name=score.criterion.name,
        score=score.score,
        comment=score.comment,
        updated_at=score.updated_at,
    )


def _scoring_out(scoring):
    return ApplicationScoringOut(
        id=scoring.id,
        application_id=scoring.application_id,
        scorer=ScorerOut(id=scoring.scorer_id, username=scoring.scorer.username),
        status=scoring.status,
        submitted_at=scoring.submitted_at,
        scores=[_score_out(s) for s in scoring.scores.select_related("criterion").all()],
        created_at=scoring.created_at,
        updated_at=scoring.updated_at,
    )


def _validate_score_value(criterion, value):
    if value < 0 or value > criterion.max_score:
        raise HttpError(
            400,
            f"Score for '{criterion.name}' must be between 0 and {criterion.max_score}.",
        )
    if criterion.score_type == ScoringCriterion.ScoreType.BOOLEAN:
        if value not in (Decimal("0"), criterion.max_score):
            raise HttpError(
                400,
                f"Boolean score for '{criterion.name}' must be 0 or {criterion.max_score}.",
            )


# ---------- Scoring criteria ----------


@router.get(
    "/scoring-criteria",
    response=list[ScoringCriterionOut],
    tags=["Scoring"],
    summary="List scoring criteria",
    operation_id="listScoringCriteria",
)
def list_scoring_criteria(request, include_inactive: bool = False):
    _require_perm(request, PERM_VIEW_CRITERIA)

    criteria = ScoringCriterion.objects.all().order_by("order", "name")
    if include_inactive and not _has_perm(request, PERM_MANAGE_CRITERIA):
        raise HttpError(403, "You do not have permission to view inactive criteria.")
    if not include_inactive:
        criteria = criteria.filter(is_active=True)
    return [_criterion_out(c) for c in criteria]


@router.post(
    "/scoring-criteria",
    response={201: ScoringCriterionOut},
    tags=["Scoring"],
    summary="Create a scoring criterion",
    operation_id="createScoringCriterion",
)
@csrf_exempt
def create_scoring_criterion(request, payload: ScoringCriterionIn):
    _require_perm(request, PERM_MANAGE_CRITERIA)

    criterion = ScoringCriterion(
        name=payload.name,
        description=payload.description,
        weight=payload.weight,
        max_score=payload.max_score,
        score_type=payload.score_type,
        is_required=payload.is_required,
        is_active=payload.is_active,
        order=payload.order,
    )
    try:
        criterion.full_clean()
        criterion.save()
    except Exception as error:  # noqa: BLE001
        if hasattr(error, "message_dict"):
            _raise_validation_error(error)
        raise
    return 201, _criterion_out(criterion)


@router.get(
    "/scoring-criteria/{criterion_id}",
    response=ScoringCriterionOut,
    tags=["Scoring"],
    summary="Get a scoring criterion",
    operation_id="getScoringCriterion",
)
def get_scoring_criterion(request, criterion_id: int):
    _require_perm(request, PERM_VIEW_CRITERIA)
    try:
        criterion = ScoringCriterion.objects.get(id=criterion_id)
    except ScoringCriterion.DoesNotExist:
        raise HttpError(404, "Scoring criterion not found")
    return _criterion_out(criterion)


@router.patch(
    "/scoring-criteria/{criterion_id}",
    response=ScoringCriterionOut,
    tags=["Scoring"],
    summary="Update a scoring criterion",
    operation_id="updateScoringCriterion",
)
@csrf_exempt
def update_scoring_criterion(request, criterion_id: int, payload: ScoringCriterionIn):
    _require_perm(request, PERM_MANAGE_CRITERIA)
    try:
        criterion = ScoringCriterion.objects.get(id=criterion_id)
    except ScoringCriterion.DoesNotExist:
        raise HttpError(404, "Scoring criterion not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(criterion, field, value)
    try:
        criterion.full_clean()
        criterion.save()
    except Exception as error:  # noqa: BLE001
        if hasattr(error, "message_dict") or hasattr(error, "messages"):
            _raise_validation_error(error)
        raise
    return _criterion_out(criterion)


@router.delete(
    "/scoring-criteria/{criterion_id}",
    response={200: dict},
    tags=["Scoring"],
    summary="Delete a scoring criterion",
    operation_id="deleteScoringCriterion",
)
@csrf_exempt
def delete_scoring_criterion(request, criterion_id: int):
    _require_perm(request, PERM_MANAGE_CRITERIA)
    try:
        criterion = ScoringCriterion.objects.get(id=criterion_id)
    except ScoringCriterion.DoesNotExist:
        raise HttpError(404, "Scoring criterion not found")

    from django.db.models.deletion import ProtectedError

    try:
        criterion.delete()
    except ProtectedError:
        raise HttpError(
            400,
            "This criterion is referenced by existing scores and cannot be deleted. "
            "Deactivate it instead (is_active=false).",
        )
    return {"success": True}


# ---------- Scoring sessions ----------


def _get_scoring(application_id, scoring_id):
    try:
        scoring = ApplicationScoring.objects.select_related("application", "scorer").get(
            id=scoring_id, application_id=application_id
        )
    except ApplicationScoring.DoesNotExist:
        raise HttpError(404, "Scoring session not found")
    return scoring


@router.get(
    "/applications/{application_id}/scorings",
    response=list[ApplicationScoringOut],
    tags=["Scoring"],
    summary="List scoring sessions for an application",
    operation_id="listApplicationScorings",
)
def list_application_scorings(request, application_id: str):
    application = _get_application(application_id)
    if not (_has_perm(request, PERM_SCORE_APPLICATION) or _has_perm(request, PERM_VIEW_ALL_SCORES)):
        raise HttpError(403, "You do not have permission to view scorings.")

    sessions = ApplicationScoring.objects.filter(application=application).select_related("scorer").prefetch_related("scores__criterion")
    if not _has_perm(request, PERM_VIEW_ALL_SCORES):
        sessions = sessions.filter(scorer=request.auth)
    return [_scoring_out(s) for s in sessions]


@router.get(
    "/applications/{application_id}/scorings/me",
    response=ApplicationScoringOut,
    tags=["Scoring"],
    summary="Get the caller's scoring session",
    operation_id="getMyScoring",
)
def get_my_scoring(request, application_id: str):
    application = _get_application(application_id)
    if not (_has_perm(request, PERM_SCORE_APPLICATION) or _has_perm(request, PERM_VIEW_ALL_SCORES)):
        raise HttpError(403, "You do not have permission to view scorings.")
    try:
        scoring = ApplicationScoring.objects.select_related("scorer").prefetch_related("scores__criterion").get(
            application=application, scorer=request.auth
        )
    except ApplicationScoring.DoesNotExist:
        raise HttpError(404, "Scoring session not found")
    return _scoring_out(scoring)


@router.put(
    "/applications/{application_id}/scorings/me",
    response=ApplicationScoringOut,
    tags=["Scoring"],
    summary="Create or update the caller's draft scoring session",
    operation_id="upsertMyScoring",
)
@csrf_exempt
def upsert_my_scoring(request, application_id: str, payload: ApplicationScoringUpsert):
    _require_perm(request, PERM_SCORE_APPLICATION)
    application = _get_application(application_id)

    scoring, _ = ApplicationScoring.objects.get_or_create(
        application=application, scorer=request.auth
    )
    if scoring.status == ApplicationScoring.Status.SUBMITTED and not _has_perm(request, PERM_FINALIZE_SCORING):
        raise HttpError(403, "Submitted scoring sessions cannot be edited.")

    # Validate batch.
    seen = set()
    validated = []
    for item in payload.scores:
        if item.criterion_id in seen:
            raise HttpError(400, "Duplicate criterion in scoring batch.")
        seen.add(item.criterion_id)
        try:
            criterion = ScoringCriterion.objects.get(id=item.criterion_id)
        except ScoringCriterion.DoesNotExist:
            raise HttpError(400, f"Scoring criterion {item.criterion_id} not found.")
        if not criterion.is_active:
            raise HttpError(400, f"Scoring criterion '{criterion.name}' is inactive.")
        _validate_score_value(criterion, item.score)
        validated.append((criterion, item))

    for criterion, item in validated:
        ApplicationScore.objects.update_or_create(
            scoring=scoring,
            criterion=criterion,
            defaults={"score": item.score, "comment": item.comment},
        )

    scoring.save()
    scoring = ApplicationScoring.objects.select_related("scorer").prefetch_related("scores__criterion").get(id=scoring.id)
    return _scoring_out(scoring)


@router.post(
    "/applications/{application_id}/scorings/me/submit",
    response=ApplicationScoringOut,
    tags=["Scoring"],
    summary="Submit the caller's scoring session",
    operation_id="submitMyScoring",
)
@csrf_exempt
def submit_my_scoring(request, application_id: str):
    _require_perm(request, PERM_SCORE_APPLICATION)
    application = _get_application(application_id)

    try:
        scoring = ApplicationScoring.objects.select_related("scorer").prefetch_related("scores__criterion").get(
            application=application, scorer=request.auth
        )
    except ApplicationScoring.DoesNotExist:
        raise HttpError(404, "Scoring session not found")

    if scoring.status == ApplicationScoring.Status.SUBMITTED:
        return _scoring_out(scoring)

    required_criteria = ScoringCriterion.objects.filter(is_active=True, is_required=True)
    scored_ids = set(scoring.scores.values_list("criterion_id", flat=True))
    missing = [c.name for c in required_criteria if c.id not in scored_ids]
    if missing:
        raise HttpError(400, "Missing required criteria: " + ", ".join(missing) + ".")

    scoring.status = ApplicationScoring.Status.SUBMITTED
    scoring.submitted_at = timezone.now()
    scoring.save()
    return _scoring_out(scoring)


@router.get(
    "/applications/{application_id}/scorings/{scoring_id}",
    response=ApplicationScoringOut,
    tags=["Scoring"],
    summary="Get a scoring session",
    operation_id="getApplicationScoring",
)
def get_application_scoring(request, application_id: str, scoring_id: int):
    application = _get_application(application_id)
    scoring = _get_scoring(application_id, scoring_id)
    if scoring.application_id != application.id:
        raise HttpError(404, "Scoring session not found")
    if not (_has_perm(request, PERM_VIEW_ALL_SCORES) or scoring.scorer_id == request.auth.id):
        raise HttpError(403, "You do not have permission to view this scoring.")
    scoring = ApplicationScoring.objects.select_related("scorer").prefetch_related("scores__criterion").get(id=scoring.id)
    return _scoring_out(scoring)


@router.patch(
    "/applications/{application_id}/scorings/{scoring_id}",
    response=ApplicationScoringOut,
    tags=["Scoring"],
    summary="Edit a scoring session",
    operation_id="patchApplicationScoring",
)
@csrf_exempt
def patch_application_scoring(request, application_id: str, scoring_id: int, payload: ApplicationScoringPatch):
    application = _get_application(application_id)
    scoring = _get_scoring(application_id, scoring_id)
    if scoring.application_id != application.id:
        raise HttpError(404, "Scoring session not found")

    if scoring.status == ApplicationScoring.Status.SUBMITTED and not _has_perm(request, PERM_FINALIZE_SCORING):
        raise HttpError(403, "Submitted scoring sessions cannot be edited.")
    if scoring.scorer_id != request.auth.id and not _has_perm(request, PERM_FINALIZE_SCORING):
        raise HttpError(403, "You do not have permission to edit this scoring.")

    if payload.status is not None:
        if payload.status not in ("draft", "submitted"):
            raise HttpError(400, "Invalid status.")
        scoring.status = payload.status
        if payload.status == "submitted" and scoring.submitted_at is None:
            scoring.submitted_at = timezone.now()

    if payload.scores is not None:
        seen = set()
        validated = []
        for item in payload.scores:
            if item.criterion_id in seen:
                raise HttpError(400, "Duplicate criterion in scoring batch.")
            seen.add(item.criterion_id)
            try:
                criterion = ScoringCriterion.objects.get(id=item.criterion_id)
            except ScoringCriterion.DoesNotExist:
                raise HttpError(400, f"Scoring criterion {item.criterion_id} not found.")
            if not criterion.is_active:
                raise HttpError(400, f"Scoring criterion '{criterion.name}' is inactive.")
            _validate_score_value(criterion, item.score)
            validated.append((criterion, item))
        for criterion, item in validated:
            ApplicationScore.objects.update_or_create(
                scoring=scoring,
                criterion=criterion,
                defaults={"score": item.score, "comment": item.comment},
            )

    scoring.save()
    scoring = ApplicationScoring.objects.select_related("scorer").prefetch_related("scores__criterion").get(id=scoring.id)
    return _scoring_out(scoring)


@router.delete(
    "/applications/{application_id}/scorings/{scoring_id}",
    response={200: dict},
    tags=["Scoring"],
    summary="Delete a scoring session",
    operation_id="deleteApplicationScoring",
)
@csrf_exempt
def delete_application_scoring(request, application_id: str, scoring_id: int):
    application = _get_application(application_id)
    scoring = _get_scoring(application_id, scoring_id)
    if scoring.application_id != application.id:
        raise HttpError(404, "Scoring session not found")

    is_owner = scoring.scorer_id == request.auth.id
    is_draft = scoring.status == ApplicationScoring.Status.DRAFT
    if not (is_owner and is_draft) and not _has_perm(request, PERM_FINALIZE_SCORING):
        raise HttpError(403, "You do not have permission to delete this scoring.")

    scoring.delete()
    return {"success": True}


@router.get(
    "/applications/{application_id}/scoring-summary",
    response=ApplicationScoringSummary,
    tags=["Scoring"],
    summary="Scoring summary for an application",
    operation_id="getApplicationScoringSummary",
)
def get_scoring_summary(request, application_id: str, include_drafts: bool = False):
    _require_perm(request, PERM_VIEW_ALL_SCORES)
    application = _get_application(application_id)

    if include_drafts and not _has_perm(request, PERM_FINALIZE_SCORING):
        include_drafts = False

    summary = scoring_summary(application, include_drafts=include_drafts)
    return ApplicationScoringSummary(
        application_id=application.id,
        scorers=[
            ScorerTotalOut(
                scorer_id=r["scorer_id"],
                username=r["username"],
                status=r["status"],
                total_raw=r["total_raw"],
                total_weighted=r["total_weighted"],
            )
            for r in summary["scorers"]
        ],
        criteria=[
            CriterionMeanOut(
                criterion_id=c["criterion_id"],
                name=c["name"],
                mean_score=c["mean_score"],
                weight=c["weight"],
            )
            for c in summary["criteria"]
        ],
        overall_weighted_mean=summary["overall_weighted_mean"],
    )
