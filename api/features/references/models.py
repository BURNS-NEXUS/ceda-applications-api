from cuid2 import Cuid
from django.db import models

from api.base_models import BaseModel

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


class BaseModelWithApplication(BaseModel):
    application = models.ForeignKey(
        "api.Application",
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class References(BaseModelWithApplication):
    name = models.CharField(max_length=255)
    postal_address = models.CharField(max_length=255)
    cell_phone = models.CharField(max_length=255)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012


class ReferencesCommercialBankers(BaseModelWithApplication):
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    branch = models.CharField(max_length=255)
    cell_phone = models.CharField(max_length=255)
    accountants_auditor = models.TextField(max_length=255)
    company_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    contact_person_address = models.CharField(max_length=255)
    contact_person_cell_phone = models.CharField(max_length=255)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012


class NextOfKin(BaseModelWithApplication):
    name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=255)
    id_number = models.CharField(max_length=255)
    postal_address = models.CharField(max_length=255)
    physical_address = models.CharField(max_length=255)
    cell_phone = models.CharField(max_length=255)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
