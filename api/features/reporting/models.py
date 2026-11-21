from django.conf import settings
from django.db import models

from api.base_models import BaseModel


class ReportTemplate(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    filters = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_templates",
    )

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
        permissions = [  # noqa: RUF012
            ("view_reports", "Can view application processing reports"),
            ("manage_report_templates", "Can create and manage report templates"),
        ]

    def __str__(self):
        return self.name