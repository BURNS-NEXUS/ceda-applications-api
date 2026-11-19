import django_fsm as fsm
from cuid2 import Cuid
from django.conf import settings
from django.db import models

from api.features.audit_logs.models import AuditLog

from .permissions import can_submit_applications, can_view_all_applications

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


class Application(fsm.FSMModelMixin, models.Model):
    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
    state = fsm.FSMField(default="draft", protected=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    project_title = models.CharField(max_length=255)
    company_no = models.CharField(max_length=255)
    incorporation_date = models.DateField()
    contact_person = models.CharField(max_length=255)
    telephone = models.CharField(max_length=255)
    business_nature = models.CharField(max_length=255)
    business_location = models.CharField(max_length=255)
    loan_amount = models.DecimalField(max_digits=10, decimal_places=2)
    email = models.EmailField()
    type = models.CharField(
        max_length=255,
        choices=[
            ("individual", "Individual"),
            ("company", "Company"),
        ],
    )
    has_current_loan_with_other = models.BooleanField(default=False)
    has_past_loan_with_other = models.BooleanField(default=False)

    # internal
    submission_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012
        permissions = [  # noqa: RUF012
            (
                can_view_all_applications,
                "Can view ALL applicantions",
            ),
            (
                can_submit_applications,
                "Can submit applications",
            ),
        ]

    def __str__(self):
        return self.project_title

    # region State  Transitions
    @fsm.transition(field=state, source="draft", target="submitted")
    def submit(self, **kwargs):
        audit_log = AuditLog.objects.create(
            actor=self.owner,
            action=f"Changed state of '{self.project_title}' from 'draft' to 'submitted'",
            resource_type="Application",
            resource_id=self.id,
            details={"state": "submitted"},
        )
        audit_log.save()
        #  We will create a task manager here to prevent one person handling multiple submissions simultaneously.

    @fsm.transition(field=state, source="submitted", target="screening")
    def begin_screening(self, **kwargs):
        audit_log = AuditLog.objects.create(
            actor=self.owner,
            action=f"Changed state of '{self.project_title}' from 'submitted' to 'screening'",
            resource_type="Application",
            resource_id=self.id,
            details={"state": "screening"},
        )
        audit_log.save()

    @fsm.transition(field=state, source="submitted", target="feedback")
    def request_feedback(self, **kwargs):
        audit_log = AuditLog.objects.create(
            actor=self.owner,
            action=f"Changed state of '{self.project_title}' from 'screening' to 'feedback'",
            resource_type="Application",
            resource_id=self.id,
            details={"state": "feedback"},
        )
        audit_log.save()

    @fsm.transition(field=state, source="feedback", target="submitted")
    def resubmit(self, **kwargs):
        audit_log = AuditLog.objects.create(
            actor=self.owner,
            action=f"Changed state of '{self.project_title}' from 'feedback' to 'submitted'",
            resource_type="Application",
            resource_id=self.id,
            details={"state": "submitted"},
        )
        audit_log.save()

    @fsm.transition(field=state, source=["submitted", "screening"], target="ineligible")
    def make_ineligible(self, **kwargs):
        audit_log = AuditLog.objects.create(
            actor=self.owner,
            action=f"Changed state of '{self.project_title}' to 'ineligible'",
            resource_type="Application",
            resource_id=self.id,
            details={"state": "ineligible"},
        )
        audit_log.save()
        # TODO: Send notification to the applicant about ineligibility

    @fsm.transition(field=state, source="screening", target="in_review")
    def make_eligible(self, **kwargs):
        audit_log = AuditLog.objects.create(
            actor=self.owner,
            action=f"Changed state of '{self.project_title}' from 'screening' to 'in_review'",
            resource_type="Application",
            resource_id=self.id,
            details={"state": "in_review"},
        )
        audit_log.save()

    # endregion
