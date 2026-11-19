from cuid2 import Cuid
from django.contrib.auth.models import AbstractUser
from django.db import models

from api.features.audit_logs.models import AuditLog
from api.features.corporate_details.models import CorporateDetails, ShareHolders
from api.features.documents.models import ApplicationDocument, DocumentType
from api.features.evaluations.models import (
    Evaluation,
    EvaluationCriterion,
    EvaluationScore,
)
from api.features.financial_details.models import Loans
from api.features.personal_details.models import (
    Address,
    Contact,
    Employment,
    PersonalDetails,
)
from api.features.references.models import (
    NextOfKin,
    References,
    ReferencesCommercialBankers,
)

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


class User(AbstractUser):
    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )


__all__ = [
    "Address",
    "ApplicationDocument",
    "AuditLog",
    "Contact",
    "CorporateDetails",
    "DocumentType",
    "Employment",
    "Evaluation",
    "EvaluationCriterion",
    "EvaluationScore",
    "Loans",
    "NextOfKin",
    "PersonalDetails",
    "References",
    "ReferencesCommercialBankers",
    "ShareHolders",
    "User",
]
