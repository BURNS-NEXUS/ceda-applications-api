from cuid2 import Cuid
from django.db import models

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


class BaseModel(models.Model):
    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
