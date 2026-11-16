from cuid2 import Cuid
from django.conf import settings
from django.db import models

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


class Application(models.Model):
    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    project_title = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012

    def __str__(self):
        return self.project_title
