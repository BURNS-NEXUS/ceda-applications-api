from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ninja import Query, Router
from ninja.errors import HttpError

from api.features.applications.models import Application
from django.contrib.auth import get_user_model

from .models import (
    ApplicationAdjudication,
    ApplicationAdjudicationScore,
    ApplicationScore,
    ApplicationScoring,
    ScoringCriterion,
)
from .schemas import (
    ApplicationAdjudicationIn,
    ApplicationAdjudicationOut,
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
    ScoringCriterionPatch,
)
from .services import (
    confirm_adjudication,
    maybe_transition_to_adjudication,
    raw_total,
    scoring_summary,
    user_can_adjudicate,
    user_can_evaluate,
    weighted_total,
)

router = Router()

PERM_MANAGE_CRITERIA = "scoring.manage_scoring_criteria"
PERM_VIEW_CRITERIA = "scoring.view_scoringcriterion"
PERM_SCORE_APPLICATION = "scoring.score_application"
PERM_VIEW_ALL_SCORES = "scoring.view_all_scores"
PERM_FINALIZE_SCORING = "scoring.finalize_scoring"
PERM_ADJUDICATE_APPLICATION = "scoring.adjudicate_application"


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
        confirmed_at=scoring.confirmed_at,
        scores=[
            _score_out(s) for s in scoring.scores.select_related("criterion").all()
        ],
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
def update_scoring_criterion(
    request, criterion_id: int, payload: ScoringCriterionPatch
):
    _require_perm(request, PERM_MANAGE_CRITERIA)
    try:
        criterion = ScoringCriterion.objects.get(id=criterion_id)
    except ScoringCriterion.DoesNotExist:
        raise HttpError(404, "Scoring criterion not found")

    data = payload.model_dump(exclude_unset=True, exclude_none=True)
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
        scoring = ApplicationScoring.objects.select_related(
            "application", "scorer"
        ).get(id=scoring_id, application_id=application_id)
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

    sessions = (
        ApplicationScoring.objects.filter(application=application)
        .select_related("scorer")
        .prefetch_related("scores__criterion")
    )
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
    if not (
        _has_perm(request, PERM_SCORE_APPLICATION)
        or _has_perm(request, PERM_VIEW_ALL_SCORES)
    ):
        raise HttpError(403, "You do not have permission to view scorings.")
    if not _has_perm(request, PERM_VIEW_ALL_SCORES):
        try:
            existing = ApplicationScoring.objects.get(
                application=application, scorer=request.auth
            )
            if existing.scorer_id != request.auth.id:
                raise HttpError(403, "You are not assigned to score this application.")
        except ApplicationScoring.DoesNotExist:
            if not user_can_evaluate(request.auth, application):
                raise HttpError(403, "You are not assigned to score this application.")
    try:
        scoring = (
            ApplicationScoring.objects.select_related("scorer")
            .prefetch_related("scores__criterion")
            .get(application=application, scorer=request.auth)
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
    if scoring.status == ApplicationScoring.Status.CONFIRMED:
        raise HttpError(400, "Scoring is confirmed and cannot be changed")
    if not user_can_evaluate(request.auth, application):
        raise HttpError(403, "You are not assigned to score this application.")

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
    scoring = (
        ApplicationScoring.objects.select_related("scorer")
        .prefetch_related("scores__criterion")
        .get(id=scoring.id)
    )
    return _scoring_out(scoring)


@router.post(
    "/applications/{application_id}/scorings/me/confirm",
    response=ApplicationScoringOut,
    tags=["Scoring"],
    summary="Confirm the caller's scoring session",
    operation_id="confirmMyScoring",
)
@csrf_exempt
def confirm_my_scoring(request, application_id: str):
    _require_perm(request, PERM_SCORE_APPLICATION)
    application = _get_application(application_id)
    if not user_can_evaluate(request.auth, application):
        raise HttpError(403, "You are not assigned to score this application.")

    try:
        scoring = (
            ApplicationScoring.objects.select_related("scorer")
            .prefetch_related("scores__criterion")
            .get(application=application, scorer=request.auth)
        )
    except ApplicationScoring.DoesNotExist:
        raise HttpError(404, "Scoring session not found")

    if scoring.status == ApplicationScoring.Status.CONFIRMED:
        return _scoring_out(scoring)

    required_criteria = ScoringCriterion.objects.filter(
        is_active=True, is_required=True
    )
    scored_ids = set(scoring.scores.values_list("criterion_id", flat=True))
    missing = [c.name for c in required_criteria if c.id not in scored_ids]
    if missing:
        raise HttpError(400, "Missing required criteria: " + ", ".join(missing) + ".")

    with transaction.atomic():
        application_locked = Application.objects.select_for_update().get(
            pk=application.pk
        )
        scoring.status = ApplicationScoring.Status.CONFIRMED
        scoring.confirmed_at = timezone.now()
        scoring.submitted_at = scoring.confirmed_at
        scoring.save(
            update_fields=["status", "confirmed_at", "submitted_at", "updated_at"]
        )
        maybe_transition_to_adjudication(application_locked, actor=request.auth)
        from api.features.audit_logs.models import AuditLog

        AuditLog.objects.create(
            actor=request.auth,
            action=f"Confirmed scoring for application {application.id}",
            resource_type="ApplicationScoring",
            resource_id=scoring.id,
            details={"application_id": application.id},
        )

    scoring = (
        ApplicationScoring.objects.select_related("scorer")
        .prefetch_related("scores__criterion")
        .get(id=scoring.id)
    )
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
    if not (
        _has_perm(request, PERM_VIEW_ALL_SCORES) or scoring.scorer_id == request.auth.id
    ):
        raise HttpError(403, "You do not have permission to view this scoring.")
    scoring = (
        ApplicationScoring.objects.select_related("scorer")
        .prefetch_related("scores__criterion")
        .get(id=scoring.id)
    )
    return _scoring_out(scoring)


@router.patch(
    "/applications/{application_id}/scorings/{scoring_id}",
    response=ApplicationScoringOut,
    tags=["Scoring"],
    summary="Edit a scoring session",
    operation_id="patchApplicationScoring",
)
@csrf_exempt
def patch_application_scoring(
    request, application_id: str, scoring_id: int, payload: ApplicationScoringPatch
):
    application = _get_application(application_id)
    scoring = _get_scoring(application_id, scoring_id)
    if scoring.application_id != application.id:
        raise HttpError(404, "Scoring session not found")

    if scoring.status == ApplicationScoring.Status.CONFIRMED:
        raise HttpError(400, "Scoring is confirmed and cannot be changed")
    if scoring.scorer_id != request.auth.id and not _has_perm(
        request, PERM_FINALIZE_SCORING
    ):
        raise HttpError(403, "You do not have permission to edit this scoring.")

    if payload.status is not None:
        if payload.status not in ("draft", "confirmed"):
            raise HttpError(400, "Invalid status.")
        scoring.status = payload.status
        if payload.status == "confirmed" and scoring.confirmed_at is None:
            scoring.confirmed_at = timezone.now()
            scoring.submitted_at = scoring.confirmed_at

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
                raise HttpError(
                    400, f"Scoring criterion {item.criterion_id} not found."
                )
            if not criterion.is_active:
                raise HttpError(
                    400, f"Scoring criterion '{criterion.name}' is inactive."
                )
            _validate_score_value(criterion, item.score)
            validated.append((criterion, item))
        for criterion, item in validated:
            ApplicationScore.objects.update_or_create(
                scoring=scoring,
                criterion=criterion,
                defaults={"score": item.score, "comment": item.comment},
            )

    scoring.save()
    scoring = (
        ApplicationScoring.objects.select_related("scorer")
        .prefetch_related("scores__criterion")
        .get(id=scoring.id)
    )
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


# ---------- Adjudication ----------


def _adjudication_out(adj):
    return ApplicationAdjudicationOut(
        id=adj.id,
        application_id=adj.application_id,
        adjudicator=ScorerOut(id=adj.adjudicator_id, username=adj.adjudicator.username),
        final_score=adj.final_score,
        comment=adj.comment,
        status=adj.status,
        scores=[_score_out(score) for score in adj.scores.all()],
        confirmed_at=adj.confirmed_at,
        created_at=adj.created_at,
        updated_at=adj.updated_at,
    )


@router.get(
    "/applications/{application_id}/adjudication",
    response=ApplicationAdjudicationOut,
    tags=["Scoring"],
    summary="Get adjudication for an application",
    operation_id="getApplicationAdjudication",
)
def get_application_adjudication(request, application_id: str):
    application = _get_application(application_id)
    if not (
        _has_perm(request, PERM_VIEW_ALL_SCORES)
        or user_can_adjudicate(request.auth, application)
    ):
        raise HttpError(403, "You do not have permission to view adjudication.")

    try:
        adj = (
            ApplicationAdjudication.objects.select_related("adjudicator")
            .prefetch_related("scores__criterion")
            .get(application=application)
        )
    except ApplicationAdjudication.DoesNotExist:
        raise HttpError(404, "Adjudication not found")
    return _adjudication_out(adj)


@router.put(
    "/applications/{application_id}/adjudication",
    response=ApplicationAdjudicationOut,
    tags=["Scoring"],
    summary="Set adjudication criterion scores",
    operation_id="updateApplicationAdjudication",
)
@csrf_exempt
def update_application_adjudication(
    request, application_id: str, payload: ApplicationAdjudicationIn
):
    _require_perm(request, PERM_ADJUDICATE_APPLICATION)
    application = _get_application(application_id)
    if not user_can_adjudicate(request.auth, application):
        raise HttpError(403, "You are not assigned to adjudicate this application.")

    adj, _ = ApplicationAdjudication.objects.get_or_create(
        application=application,
        defaults={"adjudicator": request.auth},
    )
    if adj.adjudicator_id != request.auth.id:
        raise HttpError(403, "You are not the assigned adjudicator.")
    if adj.status == ApplicationAdjudication.Status.CONFIRMED:
        raise HttpError(400, "Adjudication is confirmed and cannot be changed.")

    criterion_ids = [item.criterion_id for item in payload.scores]
    if len(criterion_ids) != len(set(criterion_ids)):
        raise HttpError(400, "Duplicate scoring criteria are not allowed.")

    criteria = ScoringCriterion.objects.filter(id__in=criterion_ids)
    criteria_by_id = {criterion.id: criterion for criterion in criteria}
    if len(criteria_by_id) != len(set(criterion_ids)):
        raise HttpError(400, "One or more scoring criteria were not found.")

    validated_scores = []
    final_score = Decimal("0")
    for item in payload.scores:
        criterion = criteria_by_id[item.criterion_id]
        if not criterion.is_active:
            raise HttpError(
                400, f"Scoring criterion '{criterion.name}' is inactive."
            )
        _validate_score_value(criterion, item.score)
        validated_scores.append((criterion, item))
        final_score += item.score * criterion.weight

    try:
        with transaction.atomic():
            if payload.comment is not None:
                adj.comment = payload.comment
            adj.final_score = final_score
            adj.full_clean()
            adj.save()
            adj.scores.exclude(criterion_id__in=criterion_ids).delete()
            for criterion, item in validated_scores:
                score, _ = ApplicationAdjudicationScore.objects.update_or_create(
                    adjudication=adj,
                    criterion=criterion,
                    defaults={"score": item.score, "comment": item.comment},
                )
                score.full_clean()
    except Exception as error:  # noqa: BLE001
        if hasattr(error, "message_dict") or hasattr(error, "messages"):
            _raise_validation_error(error)
        raise
    adj = (
        ApplicationAdjudication.objects.select_related("adjudicator")
        .prefetch_related("scores__criterion")
        .get(pk=adj.pk)
    )
    return _adjudication_out(adj)


@router.post(
    "/applications/{application_id}/adjudication/confirm",
    response=ApplicationAdjudicationOut,
    tags=["Scoring"],
    summary="Confirm adjudication",
    operation_id="confirmApplicationAdjudication",
)
@csrf_exempt
def confirm_application_adjudication(request, application_id: str):
    _require_perm(request, PERM_ADJUDICATE_APPLICATION)
    application = _get_application(application_id)
    if not user_can_adjudicate(request.auth, application):
        raise HttpError(403, "You are not assigned to adjudicate this application.")

    try:
        adj = ApplicationAdjudication.objects.select_related("adjudicator").get(
            application=application
        )
    except ApplicationAdjudication.DoesNotExist:
        raise HttpError(404, "Adjudication not found")

    if adj.adjudicator_id != request.auth.id:
        raise HttpError(403, "You are not the assigned adjudicator.")
    if adj.status == ApplicationAdjudication.Status.CONFIRMED:
        raise HttpError(400, "Adjudication is already confirmed.")
    required_ids = set(
        ScoringCriterion.objects.filter(is_active=True, is_required=True).values_list(
            "id", flat=True
        )
    )
    scored_ids = set(adj.scores.values_list("criterion_id", flat=True))
    missing_ids = required_ids - scored_ids
    if missing_ids:
        missing = ScoringCriterion.objects.filter(id__in=missing_ids).values_list(
            "name", flat=True
        )
        raise HttpError(400, "Missing required criteria: " + ", ".join(missing) + ".")

    with transaction.atomic():
        try:
            confirm_adjudication(application, request.auth)
        except (ValueError, PermissionError) as error:
            raise HttpError(400, str(error))
    adj.refresh_from_db()
    adj = (
        ApplicationAdjudication.objects.select_related("adjudicator")
        .prefetch_related("scores__criterion")
        .get(application=application)
    )
    return _adjudication_out(adj)
