from django.core.management.base import BaseCommand

from api.features.applications.models import Application
from api.features.tasks.models import TaskAssignment
from api.features.tasks.services import ensure_task_for_application, retry_pending_tasks


class Command(BaseCommand):
    help = "Create and assign verification/adjudication tasks; leave evaluation tasks in the claim pool."

    def handle(self, *args, **options):
        assigned_before = TaskAssignment.objects.count()
        for application in Application.objects.filter(
            state__in=[
                "verification",
                "evaluation",
                "scoring",
                "adjudication",
            ]
        ):
            ensure_task_for_application(application)
        assigned = TaskAssignment.objects.count() - assigned_before
        assigned += retry_pending_tasks()
        self.stdout.write(
            self.style.SUCCESS(f"Assigned {assigned} pending task slot(s).")
        )
