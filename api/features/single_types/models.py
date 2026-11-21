from django.core.validators import MinValueValidator
from django.db import models

from api.base_models import SingletonModel


class SystemSettings(SingletonModel):
    """Application-wide configuration managed through the ``/settings`` endpoints."""

    site_name = models.CharField(
        max_length=100,
        default="My App",
        help_text="Public name of the application.",
    )
    maintenance_mode = models.BooleanField(
        default=False,
        help_text="When enabled, clients should show a maintenance notice.",
    )
    evaluators_per_application = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(1)],
        help_text="Number of evaluators assigned to each application.",
    )
    minimum_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Minimum adjudication score required for acceptance.",
    )

    class Meta:
        verbose_name = "System settings"
        verbose_name_plural = "System settings"

    def __str__(self):
        return "System settings"
