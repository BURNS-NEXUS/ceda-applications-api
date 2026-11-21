from django.contrib import admin

from .models import ReportTemplate


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")