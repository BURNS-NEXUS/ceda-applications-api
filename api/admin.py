from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .features.applications.models import Application
from .features.audit_logs.models import AuditLog
from .features.clarifications.models import Clarification
from .features.corporate_details.models import CorporateDetails, ShareHolders
from .features.documents.models import ApplicationDocument, DocumentType
from .features.documents.validators import DOCUMENT_FILE_TYPE_CHOICES
from .features.evaluations.models import (
    Evaluation,
    EvaluationCriterion,
    EvaluationScore,
)
from .features.financial_details.models import Loans
from .features.personal_details.models import (
    Address,
    Contact,
    Employment,
    PersonalDetails,
)
from .features.references.models import (
    NextOfKin,
    References,
    ReferencesCommercialBankers,
)
from .models import User


class DocumentTypeAdminForm(forms.ModelForm):
    allowed_file_types = forms.MultipleChoiceField(
        choices=DOCUMENT_FILE_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        help_text="File type families accepted for this document.",
    )

    class Meta:
        model = DocumentType
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["allowed_file_types"] = (
                self.instance.allowed_file_types or []
            )

    def clean_allowed_file_types(self):
        return list(self.cleaned_data["allowed_file_types"])


class AllowedFileTypesFilter(admin.SimpleListFilter):
    title = "allowed file types"
    parameter_name = "allowed_file_type"

    def lookups(self, request, model_admin):
        return DOCUMENT_FILE_TYPE_CHOICES

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        matching = [
            document_type.pk
            for document_type in DocumentType.objects.all()
            if value in (document_type.allowed_file_types or [])
        ]
        return queryset.filter(pk__in=matching)


class DocumentTypeAdmin(admin.ModelAdmin):
    form = DocumentTypeAdminForm
    list_display = (
        "name",
        "allowed_file_types_display",
        "is_required",
        "is_active",
        "created_at",
    )
    list_filter = ("is_required", "is_active", AllowedFileTypesFilter)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)


class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 0
    can_delete = False
    show_change_link = True
    fields = (
        "document_type",
        "file",
        "file_description",
        "status",
        "reason",
        "rejected_by",
        "decision_on",
        "created_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "project_title", "state", "submission_count", "owner")
    list_filter = ("owner",)
    search_fields = ("project_title",)
    inlines = (ApplicationDocumentInline,)


class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "document_type",
        "status",
        "rejected_by",
        "decision_on",
        "created_at",
    )
    list_filter = ("status", "document_type", "decision_on")
    search_fields = ("application__id", "file_description", "document_type__name")
    readonly_fields = ("decision_on", "rejected_by", "created_at", "updated_at")
    list_select_related = ("application", "document_type", "rejected_by")

    def save_model(self, request, obj, form, change):
        if obj.status == ApplicationDocument.Status.REJECTED:
            obj.rejected_by = request.user
            obj.decision_on = timezone.now()
        elif obj.status == ApplicationDocument.Status.ACCEPTED:
            obj.rejected_by = None
            obj.decision_on = timezone.now()
        else:
            obj.reason = ""
            obj.rejected_by = None
            obj.decision_on = None
        super().save_model(request, obj, form, change)


class ClarificationAdmin(admin.ModelAdmin):
    list_display = ("id", "version", "application", "reason")
    list_filter = ("application",)
    search_fields = ("project_title",)


class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "actor", "action", "resource_type", "created_at")
    list_filter = ("resource_type", "created_at")
    search_fields = ("action", "resource_type", "resource_id", "actor__username")


class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "postal_address",
        "physical_address",
        "duration_of_stay",
    )
    list_filter = ("application",)
    search_fields = (
        "application__project_title",
        "postal_address",
        "physical_address",
    )


class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "contact_type", "contact_value", "email")
    list_filter = ("contact_type", "application")
    search_fields = ("application__project_title", "contact_value", "email")


class CorporateDetailsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "name_of_company",
        "date_of_incorporation",
        "nature_of_company",
    )
    list_filter = ("date_of_incorporation", "nature_of_company")
    search_fields = (
        "application__project_title",
        "name_of_company",
        "nature_of_company",
    )


class EmploymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "employer_name",
        "job_title",
        "salary_per_month",
    )
    list_filter = ("ever_applied_for_loan", "job_title")
    search_fields = (
        "application__project_title",
        "employer_name",
        "job_title",
    )


class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "evaluator", "created_at")
    list_filter = ("evaluator", "created_at")
    search_fields = (
        "application__project_title",
        "evaluator__username",
        "comments",
    )


class EvaluationCriterionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "maximum_score", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")


class EvaluationScoreAdmin(admin.ModelAdmin):
    list_display = ("id", "evaluation", "criterion", "score")
    list_filter = ("criterion",)
    search_fields = (
        "evaluation__application__project_title",
        "evaluation__evaluator__username",
        "criterion__name",
        "comments",
    )


class LoansAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "institution_name",
        "loan_amount",
        "amount_outstanding",
        "is_past_loan",
    )
    list_filter = ("institution_name", "is_past_loan")
    search_fields = (
        "application__project_title",
        "institution_name",
        "account_number",
    )


class NextOfKinAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "name", "relationship", "cell_phone")
    list_filter = ("relationship",)
    search_fields = (
        "application__project_title",
        "name",
        "id_number",
        "cell_phone",
    )


class PersonalDetailsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "title",
        "surname",
        "other_names",
        "id_number",
    )
    list_filter = ("title", "marital_status")
    search_fields = (
        "application__project_title",
        "surname",
        "other_names",
        "id_number",
    )


class ReferencesAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "name", "postal_address", "cell_phone")
    list_filter = ("application",)
    search_fields = ("application__project_title", "name", "cell_phone")


class ReferencesCommercialBankersAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "bank_name",
        "branch",
        "account_number",
        "company_name",
    )
    list_filter = ("bank_name", "branch")
    search_fields = (
        "application__project_title",
        "bank_name",
        "account_number",
        "company_name",
        "contact_person",
        "contact_person_cell_phone",
    )


class ShareHoldersAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "application",
        "company",
        "name",
        "position",
        "nationality",
        "total_issued_share_capital",
    )
    list_filter = ("position", "nationality", "company")
    search_fields = (
        "application__project_title",
        "company__name_of_company",
        "name",
        "id_number",
    )


admin.site.register(User, UserAdmin)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(ApplicationDocument, ApplicationDocumentAdmin)
admin.site.register(DocumentType, DocumentTypeAdmin)
admin.site.register(Clarification, ClarificationAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(AuditLog, AuditLogAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(CorporateDetails, CorporateDetailsAdmin)
admin.site.register(Employment, EmploymentAdmin)
admin.site.register(Evaluation, EvaluationAdmin)
admin.site.register(EvaluationCriterion, EvaluationCriterionAdmin)
admin.site.register(EvaluationScore, EvaluationScoreAdmin)
admin.site.register(Loans, LoansAdmin)
admin.site.register(NextOfKin, NextOfKinAdmin)
admin.site.register(PersonalDetails, PersonalDetailsAdmin)
admin.site.register(References, ReferencesAdmin)
admin.site.register(ReferencesCommercialBankers, ReferencesCommercialBankersAdmin)
admin.site.register(ShareHolders, ShareHoldersAdmin)
