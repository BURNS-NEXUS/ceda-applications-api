from cuid2 import Cuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


class EvaluationCriterion(models.Model):
    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    maximum_score = models.PositiveSmallIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]  # noqa: RUF012

    def __str__(self):
        return self.name


class Evaluation(models.Model):
    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    application = models.ForeignKey(
        "api.Application",
        on_delete=models.CASCADE,
        related_name="evaluations",
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="evaluations",
    )
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["application", "evaluator"],
                name="unique_evaluation_per_evaluator",
            )
        ]

    def __str__(self):
        return f"Evaluation of {self.application} by {self.evaluator}"


class EvaluationScore(models.Model):
    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="scores",
    )
    criterion = models.ForeignKey(
        EvaluationCriterion,
        on_delete=models.PROTECT,
        related_name="evaluation_scores",
    )
    score = models.PositiveSmallIntegerField()
    comments = models.TextField(blank=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["evaluation", "criterion"],
                name="unique_score_per_evaluation_criterion",
            )
        ]

    def clean(self):
        super().clean()
        if (
            self.criterion_id
            and self.score is not None
            and self.score > self.criterion.maximum_score
        ):
            raise ValidationError(
                {
                    "score": (
                        f"Score cannot exceed the criterion maximum of "
                        f"{self.criterion.maximum_score}."
                    )
                }
            )

    def __str__(self):
        return f"{self.criterion}: {self.score}"
