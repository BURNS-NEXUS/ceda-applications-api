from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .features.applications.models import Application
from .features.audit_logs.models import AuditLog
from .features.clarifications.models import Clarification
from .features.corporate_details.models import CorporateDetails, ShareHolders
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


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "project_title", "state", "submission_count", "owner")
    list_filter = ("owner",)
    search_fields = ("project_title",)


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
