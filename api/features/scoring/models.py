from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class ScoringCriterion(models.Model):
    """Admin-managed catalog of scoring criteria."""

    class ScoreType(models.TextChoices):
        NUMERIC = "numeric", "Numeric"
        BOOLEAN = "boolean", "Boolean"

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    max_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    score_type = models.CharField(
        max_length=20,
        choices=ScoreType.choices,
        default=ScoreType.NUMERIC,
    )
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]  # noqa: RUF012
        verbose_name = "Scoring criterion"
        verbose_name_plural = "Scoring criteria"
        constraints = [  # noqa: RUF012
            models.CheckConstraint(
                condition=models.Q(weight__gte=0),
                name="scoringcriterion_weight_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(max_score__gt=0),
                name="scoringcriterion_max_score_gt_0",
            ),
        ]
        permissions = [  # noqa: RUF012
            (
                "manage_scoring_criteria",
                "Can create, update, and delete scoring criteria",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.weight is not None and self.weight < 0:
            raise ValidationError(
                {"weight": "Weight must be greater than or equal to 0."}
            )
        if self.max_score is not None and self.max_score <= 0:
            raise ValidationError(
                {"max_score": "Maximum score must be greater than 0."}
            )


class ApplicationScoring(models.Model):
    """One scoring session per scorer per application."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONFIRMED = "confirmed", "Confirmed"

    application = models.ForeignKey(
        "api.Application",
        on_delete=models.CASCADE,
        related_name="scorings",
    )
    overall_comment = models.TextField(blank=True)
    evidence_reference = models.TextField(blank=True)
    no_conflict_declared = models.BooleanField(default=False)
    scorer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="application_scorings",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
        verbose_name = "Application scoring"
        verbose_name_plural = "Application scorings"
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["application", "scorer"],
                name="unique_scoring_per_scorer_application",
            )
        ]
        permissions = [  # noqa: RUF012
            ("score_application", "Can submit scores for an application"),
            ("view_all_scores", "Can view scores of all scorers on any application"),
            (
                "finalize_scoring",
                "Can override/edit scores after submission or mark scoring complete",
            ),
        ]

    def __str__(self):
        return f"{self.application_id} by {self.scorer}"


class ApplicationScore(models.Model):
    """One score per criterion within a scoring session."""

    scoring = models.ForeignKey(
        ApplicationScoring,
        on_delete=models.CASCADE,
        related_name="scores",
    )
    criterion = models.ForeignKey(
        ScoringCriterion,
        on_delete=models.PROTECT,
        related_name="scores",
    )
    score = models.DecimalField(max_digits=6, decimal_places=2)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
        verbose_name = "Application score"
        verbose_name_plural = "Application scores"
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["scoring", "criterion"],
                name="unique_score_per_criterion_scoring",
            ),
            models.CheckConstraint(
                condition=models.Q(score__gte=0),
                name="applicationscore_score_gte_0",
            ),
        ]

    def clean(self):
        super().clean()
        if self.criterion_id is None or self.score is None:
            return
        if self.score < 0:
            raise ValidationError(
                {"score": "Score must be greater than or equal to 0."}
            )
        if self.score > self.criterion.max_score:
            raise ValidationError(
                {
                    "score": f"Score cannot exceed the criterion maximum of {self.criterion.max_score}."
                }
            )
        if self.criterion.score_type == ScoringCriterion.ScoreType.BOOLEAN:
            if self.score not in (Decimal("0"), self.criterion.max_score):
                raise ValidationError(
                    {"score": "Boolean scores must be 0 or the criterion maximum."}
                )

    def __str__(self):
        return f"{self.criterion}: {self.score}"


class ApplicationAdjudication(models.Model):
    """Final adjudication result for an application."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"

    application = models.OneToOneField(
        "api.Application",
        on_delete=models.CASCADE,
        related_name="adjudication",
    )
    adjudicator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="application_adjudications",
    )
    final_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    comment = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Application adjudication"
        verbose_name_plural = "Application adjudications"
        permissions = [  # noqa: RUF012
            ("adjudicate_application", "Can adjudicate an application"),
        ]

    def __str__(self):
        return f"Adjudication for {self.application_id}"


class ApplicationAdjudicationScore(models.Model):
    """Final score assigned by the adjudicator for one criterion."""

    adjudication = models.ForeignKey(
        ApplicationAdjudication,
        on_delete=models.CASCADE,
        related_name="scores",
    )
    criterion = models.ForeignKey(
        ScoringCriterion,
        on_delete=models.PROTECT,
        related_name="adjudication_scores",
    )
    score = models.DecimalField(max_digits=6, decimal_places=2)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["criterion__order", "criterion__name"]  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["adjudication", "criterion"],
                name="unique_adjudication_score_per_criterion",
            ),
            models.CheckConstraint(
                condition=models.Q(score__gte=0),
                name="adjudicationscore_score_gte_0",
            ),
        ]

    def clean(self):
        super().clean()
        if self.criterion_id is None or self.score is None:
            return
        if self.score < 0:
            raise ValidationError(
                {"score": "Score must be greater than or equal to 0."}
            )
        if self.score > self.criterion.max_score:
            raise ValidationError(
                {
                    "score": (
                        "Score cannot exceed the criterion maximum of "
                        f"{self.criterion.max_score}."
                    )
                }
            )
        if self.criterion.score_type == ScoringCriterion.ScoreType.BOOLEAN:
            if self.score not in (Decimal("0"), self.criterion.max_score):
                raise ValidationError(
                    {"score": "Boolean scores must be 0 or the criterion maximum."}
                )

    def __str__(self):
        return f"{self.criterion}: {self.score}"
