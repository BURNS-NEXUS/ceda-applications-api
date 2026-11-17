from cuid2 import Cuid
from django.conf import settings
from django.db import models

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


class Clarification(models.Model):
    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clarifications",
    )
    application = models.ForeignKey(
        "api.Application",
        on_delete=models.CASCADE,
        related_name="clarifications",
    )
    version = models.IntegerField(default=0)  # link it to application.submission_count
    reason = models.TextField()
    response = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012

    def __str__(self):
        return f"Clarification for {self.application} by {self.created_by}"
