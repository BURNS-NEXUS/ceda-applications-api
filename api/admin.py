from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .features.applications.models import Application
from .features.clarifications.models import Clarification
from .models import User


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "project_title", "state", "submission_count", "owner")
    list_filter = ("owner",)
    search_fields = ("project_title",)


class ClarificationAdmin(admin.ModelAdmin):
    list_display = ("id", "version", "application", "reason")
    list_filter = ("application",)
    search_fields = ("project_title",)


admin.site.register(User, UserAdmin)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(Clarification, ClarificationAdmin)
