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

# Source of truth: each group's permissions will be made to match this exactly.
role_permission_map = {
    "admin": [],
    "customer": [can_submit_applications],
    "evaluator": [can_view_all_applications],
}


def resolve_permissions(perm_names):
    """Turn permission codenames/strings into Permission model instances."""
    resolved = []
    for name in perm_names:
        if isinstance(name, Permission):
            resolved.append(name)
            continue

        if "." in name:
            app_label, codename = name.split(".", 1)
            qs = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            )
        else:
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
    help = "Seed roles, sync their permissions, and create default users."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        # 1. Sync roles + permissions (once per role)
        groups = {}
        role_names = set(role_permission_map) | {role for role, _ in USERS.values()}

        for role in sorted(role_names):
            group, created = Group.objects.get_or_create(name=role)
            self.report("role", role, created)
            groups[role] = group

            desired = resolve_permissions(role_permission_map.get(role, []))
            desired_ids = {p.pk for p in desired}
            current_ids = set(group.permissions.values_list("pk", flat=True))

            added = desired_ids - current_ids
            removed = current_ids - desired_ids

            # set() makes the group match `desired` exactly (adds AND removes)
            group.permissions.set(desired)

            if added or removed:
                self.stdout.write(
                    f"  Permissions for '{role}': +{len(added)} added, "
                    f"-{len(removed)} removed"
                )

        # 2. Users
        for username, (role, is_admin) in USERS.items():
            login = username if username == "admin" else f"{username}@ceda.local"

            user = User.objects.filter(username=login).first()
            if user is None:
                user = User.objects.create_user(
                    username=login,
                    email=f"{username}@ceda.local",
                    password=PASSWORD,
                    is_staff=is_admin,
                    is_superuser=is_admin,
                )
                self.report("user", username, True)
            else:
                self.report("user", username, False)

            user.groups.add(groups[role])  # idempotent

    def report(self, kind, name, created):
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created {kind} '{name}'"))
        else:
            self.stdout.write(f"{kind.capitalize()} '{name}' already exists, skipping")
