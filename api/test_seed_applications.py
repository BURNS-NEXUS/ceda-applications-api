from io import StringIO

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from api.features.applications.models import Application
from api.features.corporate_details.models import CorporateDetails, ShareHolders
from api.features.evaluations.models import (
    Evaluation,
    EvaluationCriterion,
    EvaluationScore,
)
from api.features.financial_details.models import Loans
from api.features.personal_details.models import (
    Address,
    Contact,
    Employment,
    PersonalDetails,
)
from api.features.references.models import (
    NextOfKin,
    References,
    ReferencesCommercialBankers,
)


class SeedApplicationsTests(TestCase):
    def test_seed_creates_complete_applications_and_registers_models(self):
        get_user_model().objects.create_user(username="seed-owner")

        call_command("seed_applications", stdout=StringIO())

        self.assertEqual(Application.objects.count(), 10)
        for application in Application.objects.all():
            self.assertEqual(
                References.objects.filter(application=application).count(), 2
            )
            self.assertEqual(NextOfKin.objects.filter(application=application).count(), 2)
            self.assertTrue(
                2
                <= ShareHolders.objects.filter(application=application).count()
                <= 6
            )
            for model in (
                PersonalDetails,
                Address,
                Contact,
                Employment,
                CorporateDetails,
                Loans,
                ReferencesCommercialBankers,
                Evaluation,
            ):
                self.assertTrue(model.objects.filter(application=application).exists())

        self.assertTrue(EvaluationCriterion.objects.exists())
        self.assertEqual(EvaluationScore.objects.count(), 10)

        for model in (
            Application,
            PersonalDetails,
            Address,
            Contact,
            Employment,
            CorporateDetails,
            ShareHolders,
            Loans,
            References,
            ReferencesCommercialBankers,
            NextOfKin,
            EvaluationCriterion,
            Evaluation,
            EvaluationScore,
        ):
            self.assertTrue(admin.site.is_registered(model))

        owner = application.owner
        self.client.force_login(owner)
        response = self.client.get(f"/api/applications/{application.id}")
        self.assertEqual(response.status_code, 200, response.content)
        details = response.json()
        for field in (
            "personal_details",
            "addresses",
            "contacts",
            "employments",
            "corporate_details",
            "shareholders",
            "loans",
            "references",
            "commercial_bankers",
            "next_of_kin",
            "evaluations",
            "clarifications",
        ):
            self.assertIn(field, details)
        self.assertEqual(len(details["references"]), 2)
        self.assertEqual(len(details["next_of_kin"]), 2)
        self.assertTrue(2 <= len(details["shareholders"]) <= 6)
        self.assertEqual(len(details["evaluations"]), 1)
        self.assertEqual(len(details["evaluations"][0]["scores"]), 1)
