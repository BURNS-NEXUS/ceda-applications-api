from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from api.features.applications.permissions import (
    can_submit_applications,
    can_view_all_applications,
)

PASSWORD = "ceda@321"

USERS = {
    "admin": ("admin", True),
    "customer": ("customer", False),
    "evaluator": ("evaluator", False),
    "evaluator1": ("evaluator", False),
    "evaluator2": ("evaluator", False),
    "evaluator3": ("evaluator", False),
}

customer_permissions = [
    can_submit_applications,
]
evaluator_permissions = [can_view_all_applications]
role_permission_map = {
    "customer": customer_permissions,
    "evaluator": evaluator_permissions,
}


def resolve_permissions(perm_names):
    """Turn permission codenames/strings into Permission model instances."""
    resolved = []
    for name in perm_names:
        # If it's already a Permission instance, keep it
        if isinstance(name, Permission):
            resolved.append(name)
            continue

        # If it's "app_label.codename", split it
        if "." in name:
            app_label, codename = name.split(".", 1)
            qs = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            )
        else:
            # Otherwise just match by codename
            qs = Permission.objects.filter(codename=name)

        perm = qs.first()
        if perm is None:
            raise Permission.DoesNotExist(
                f"Permission '{name}' not found in DB. "
                f"Did you run migrations and define it in Meta.permissions?"
            )
        resolved.append(perm)
    return resolved


class Command(BaseCommand):
    help = (
        "Seed the admin and customer roles and users (skips ones that already exist)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        for username, (role, is_admin) in USERS.items():
            group, created = Group.objects.get_or_create(name=role)
            self.report("role", role, created)

            # Attach permissions to the GROUP (inherited by all members)
            for perm in resolve_permissions(role_permission_map.get(role, [])):
                group.permissions.add(perm)

            user = User.objects.filter(
                username=username if username == "admin" else f"{username}@ceda.local",
            ).first()
            if user is None:
                user = User.objects.create_user(
                    username=username
                    if username == "admin"
                    else f"{username}@ceda.local",
                    email=f"{username}@ceda.local",
                    password=PASSWORD,
                    is_staff=is_admin,
                    is_superuser=is_admin,
                )
                self.report("user", username, True)
            else:
                self.report("user", username, False)

            # Idempotent — safe to call even if already a member
            user.groups.add(group)

    def report(self, kind, name, created):
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created {kind} '{name}'"))
        else:
            self.stdout.write(f"{kind.capitalize()} '{name}' already exists, skipping")
