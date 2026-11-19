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


class SingletonModel(models.Model):
    """Base model that stores exactly one row, always with primary key 1."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Singleton rows are configuration and should never be removed.
        return None

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
