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


class PersonalDetails(BaseModelWithApplication):
    title = models.CharField(max_length=255)
    surname = models.CharField(max_length=255)
    other_names = models.CharField(max_length=255)
    id_number = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    marital_status = models.CharField(max_length=255)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012


class Address(BaseModelWithApplication):
    postal_address = models.CharField(max_length=255)
    physical_address = models.CharField(max_length=255)
    duration_of_stay = models.CharField(
        max_length=255, help_text="How long have you been at this address?"
    )


class Contact(BaseModelWithApplication):
    contact_type = models.CharField(
        max_length=255,
        help_text="Type of contact (e.g, Facsimile, General, Telephone, Cell Phone)",
    )
    contact_value = models.CharField(
        max_length=255,
        help_text="Value of the contact (e.g., phone number, fax number)",
    )
    email = models.EmailField(
        max_length=255,
        help_text="Email address of the contact",
    )

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012


class Employment(BaseModelWithApplication):
    employer_name = models.CharField(max_length=255)
    employer_address = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    salary_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    training_experience = models.TextField(
        help_text="Details of any relevant training experience"
    )
    project_description = models.TextField(
        help_text="Give a brief description of the project"
    )
    ever_applied_for_loan = models.BooleanField(
        help_text="Is this the first time you have applied for Government Assistance (FAP, MBF, and CEDA)? "
    )
    loan_amount_requested = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="How much are you applying for"
    )

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
