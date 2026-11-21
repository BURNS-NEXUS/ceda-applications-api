from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from api.features.applications.permissions import (
    can_adjudicate_applications,
    can_evaluate_applications,
    can_submit_applications,
    can_verify_applications,
    can_view_all_applications,
)
from api.features.documents.permissions import (
    manage_all_application_documents,
    manage_document_types,
    review_application_document,
    view_all_application_documents,
    view_all_document_types,
)
from api.features.scoring.permissions import (
    finalize_scoring,
    manage_scoring_criteria,
    score_application,
    view_all_scores,
    view_scoringcriterion,
    adjudicate_application,
)
from api.features.single_types.permissions import change_systemsettings
from api.features.tasks.permissions import (
    can_assign_supervisor,
    can_supervise_tasks,
)

PASSWORD = "ceda@321"

USERS = {
    "admin": ("admin", True),
    "customer": ("customer", False),
    "evaluator": ("evaluator", False),
    "evaluator1": ("evaluator", False),
    "evaluator2": ("evaluator", False),
    "evaluator3": ("evaluator", False),
    "verifier1": ("verification", False),
    "verifier2": ("verification", False),
    "verifier3": ("verification", False),
    "adjudicator": ("adjudicator", False),
    "adjudicator1": ("adjudicator", False),
    "adjudicator2": ("adjudicator", False),
    "master": ("webmaster", False),
}

# Source of truth: each group's permissions will be made to match this exactly.
role_permission_map = {
    "admin": [can_assign_supervisor],
    "customer": [can_submit_applications],
    "evaluator": [
        can_evaluate_applications,
        view_scoringcriterion,
        score_application,
    ],
    "verification": [
        can_verify_applications,
        can_view_all_applications,
        review_application_document,
    ],
    "supervisor": [can_supervise_tasks],
    "adjudicator": [
        can_adjudicate_applications,
        view_scoringcriterion,
        finalize_scoring,
        view_all_scores,
        score_application,
        adjudicate_application,
    ],
    "webmaster": [
        can_assign_supervisor,
        can_supervise_tasks,
        can_adjudicate_applications,
        can_evaluate_applications,
        can_submit_applications,
        can_verify_applications,
        can_view_all_applications,
        view_all_document_types,
        manage_document_types,
        view_all_application_documents,
        manage_all_application_documents,
        review_application_document,
        change_systemsettings,
        manage_scoring_criteria,
        view_scoringcriterion,
        score_application,
        view_all_scores,
        finalize_scoring,
    ],
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
