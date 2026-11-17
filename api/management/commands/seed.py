from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

PASSWORD = "ceda@321"

# username -> (role/group name, is_staff/superuser)
USERS = {
    "admin": ("admin", True),
    "customer": ("customer", False),
}


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

            user = User.objects.filter(username=username).first()
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
            user.groups.add(group)

    def report(self, kind, name, created):
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created {kind} '{name}'"))
        else:
            self.stdout.write(f"{kind.capitalize()} '{name}' already exists, skipping")
