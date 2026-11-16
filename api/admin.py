from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User
from .features.applications.models import Application


class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "project_title", "owner")
    list_filter = ("owner",)
    search_fields = ("project_title",)


admin.site.register(User, UserAdmin)
admin.site.register(Application, ApplicationAdmin)

