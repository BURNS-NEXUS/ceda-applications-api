from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from api.features.applications.models import Application, ProgrammeCall
from api.features.documents.models import DocumentType


class SeedDemoPortalTests(TestCase):
    def test_seed_is_idempotent(self):
        get_user_model().objects.create_user(
            username="customer@ceda.local", email="customer@ceda.local"
        )

        call_command("seed_demo_portal", verbosity=0)
        first_calls = ProgrammeCall.objects.count()
        first_apps = Application.objects.count()
        self.assertEqual(first_calls, 2)
        self.assertEqual(first_apps, 3)
        self.assertEqual(DocumentType.objects.count(), 4)

        call_command("seed_demo_portal", verbosity=0)
        self.assertEqual(ProgrammeCall.objects.count(), first_calls)
        self.assertEqual(Application.objects.count(), first_apps)
        self.assertEqual(DocumentType.objects.count(), 4)

        open_call = ProgrammeCall.objects.get(published=True)
        self.assertEqual(open_call.status, "open")
        self.assertEqual(open_call.applications.count(), 3)
