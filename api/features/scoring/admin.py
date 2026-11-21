from django.contrib import admin

from .models import (
    ApplicationAdjudication,
    ApplicationScore,
    ApplicationScoring,
    ScoringCriterion,
)


class ApplicationScoreInline(admin.TabularInline):
    model = ApplicationScore
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class ScoringCriterionAdmin(admin.ModelAdmin):
    list_display = ("name", "score_type", "weight", "max_score", "is_required", "is_active", "order")
    list_filter = ("is_active", "is_required", "score_type")
    search_fields = ("name",)
    ordering = ("order", "name")

    def has_add_permission(self, request, obj=None):
        return request.user.has_perm("scoring.manage_scoring_criteria")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("scoring.manage_scoring_criteria")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("scoring.manage_scoring_criteria")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("scoring.manage_scoring_criteria") or request.user.has_perm(
            "scoring.view_scoringcriterion"
        )


class ApplicationScoringAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "scorer", "status", "submitted_at", "created_at")
    list_filter = ("status", "submitted_at")
    search_fields = ("application__id", "scorer__username")
    inlines = (ApplicationScoreInline,)

    def _submitted(self, obj):
        return bool(obj and obj.status == "confirmed")

    def has_add_permission(self, request, obj=None):
        return request.user.has_perm("scoring.add_applicationscoring")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("scoring.view_applicationscoring")

    def has_change_permission(self, request, obj=None):
        if self._submitted(obj):
            return request.user.has_perm("scoring.finalize_scoring")
        return request.user.has_perm("scoring.change_applicationscoring")

    def has_delete_permission(self, request, obj=None):
        if self._submitted(obj):
            return request.user.has_perm("scoring.finalize_scoring")
        return request.user.has_perm("scoring.delete_applicationscoring")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == "submitted" and not request.user.has_perm("scoring.finalize_scoring"):
            return ("score", "submitted_at", "scorer", "application")
        return ()


class ApplicationScoreAdmin(admin.ModelAdmin):
    list_display = ("id", "scoring", "criterion", "score", "updated_at")
    list_filter = ("criterion", "scoring__status")
    search_fields = ("scoring__application__id", "scoring__scorer__username", "criterion__name")

    def _submitted(self, obj):
        return bool(obj and obj.scoring and obj.scoring.status == "confirmed")

    def has_add_permission(self, request, obj=None):
        return request.user.has_perm("scoring.add_applicationscore")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("scoring.view_applicationscore")

    def has_change_permission(self, request, obj=None):
        if self._submitted(obj):
            return request.user.has_perm("scoring.finalize_scoring")
        return request.user.has_perm("scoring.change_applicationscore")

    def has_delete_permission(self, request, obj=None):
        if self._submitted(obj):
            return request.user.has_perm("scoring.finalize_scoring")
        return request.user.has_perm("scoring.delete_applicationscore")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.scoring and obj.scoring.status == "submitted" and not request.user.has_perm(
            "scoring.finalize_scoring"
        ):
            return ("score", "submitted_at", "scorer")
        return ()


class ApplicationAdjudicationAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "adjudicator", "status", "final_score", "confirmed_at")
    list_filter = ("status", "confirmed_at")
    search_fields = ("application__id", "adjudicator__username")
    readonly_fields = ("final_score", "comment", "confirmed_at", "created_at", "updated_at")

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(ScoringCriterion, ScoringCriterionAdmin)
admin.site.register(ApplicationScoring, ApplicationScoringAdmin)
admin.site.register(ApplicationScore, ApplicationScoreAdmin)
admin.site.register(ApplicationAdjudication, ApplicationAdjudicationAdmin)
