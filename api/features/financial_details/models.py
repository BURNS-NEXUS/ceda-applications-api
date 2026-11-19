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


class Loans(BaseModelWithApplication):
    institution_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=255)
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    repayment_amount = models.DecimalField(max_digits=10, decimal_places=2)
    repayment_period = models.IntegerField()  # in months
    amount_outstanding = models.DecimalField(max_digits=10, decimal_places=2)
    is_past_loan = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
