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


class CorporateDetails(BaseModelWithApplication):
    name_of_company = models.CharField(max_length=255)
    date_of_incorporation = models.DateField()
    nature_of_company = models.CharField(max_length=255)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012


class ShareHolders(BaseModelWithApplication):
    name = models.CharField(max_length=255)
    dob = models.DateField()
    nationality = models.CharField(max_length=255)
    id_number = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    company = models.ForeignKey(
        "api.CorporateDetails", on_delete=models.CASCADE, related_name="shareholders"
    )
    total_authorized_share_capital = models.DecimalField(
        max_digits=15, decimal_places=2
    )
    total_issued_share_capital = models.DecimalField(max_digits=15, decimal_places=2)
