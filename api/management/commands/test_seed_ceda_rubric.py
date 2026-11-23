from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from api.features.applications.models import Application
from api.features.scoring.models import (
    ApplicationScore,
    ApplicationScoring,
    ScoringCriterion,
)

from .seed_ceda_rubric import CEDA_RUBRIC


class SeedCedaRubricTests(TestCase):
    def test_seed_creates_and_updates_the_six_criteria_idempotently(self):
        call_command("seed_ceda_rubric", verbosity=0)
        call_command("seed_ceda_rubric", verbosity=0)

        criteria = list(ScoringCriterion.objects.filter(is_active=True).order_by("order"))
        self.assertEqual(len(criteria), 6)
        self.assertEqual([c.name for c in criteria], [row["name"] for row in CEDA_RUBRIC])
        for criterion, expected in zip(criteria, CEDA_RUBRIC):
            self.assertEqual(criterion.description, expected["description"])
            self.assertEqual(criterion.max_score, Decimal("5.00"))
            self.assertEqual(criterion.weight, Decimal("1.00"))
            self.assertTrue(criterion.is_required)
            self.assertTrue(criterion.is_active)
        self.assertEqual(
            [c.order for c in criteria],
            [1, 2, 3, 4, 5, 6],
        )

    def test_seed_deactivates_legacy_criteria_without_deleting_scored_rows(self):
        owner = get_user_model().objects.create_user(username="owner")
        scorer = get_user_model().objects.create_user(username="scorer")
        application = Application.objects.create(
            owner=owner,
            project_title="App",
            company_no="CO",
            incorporation_date=date(2025, 1, 1),
            contact_person="P",
            telephone="1",
            business_nature="B",
            business_location="L",
            loan_amount=100,
            email="o@example.com",
        )
        legacy = ScoringCriterion.objects.create(
            name="Innovation potential", weight=2, max_score=5
        )
        scoring = ApplicationScoring.objects.create(
            application=application, scorer=scorer
        )
        ApplicationScore.objects.create(
            scoring=scoring, criterion=legacy, score=4, comment="Legacy score."
        )

        call_command("seed_ceda_rubric", verbosity=0)

        legacy.refresh_from_db()
        self.assertFalse(legacy.is_active)
        self.assertTrue(ApplicationScore.objects.filter(criterion=legacy).exists())
        self.assertEqual(ScoringCriterion.objects.filter(is_active=True).count(), 6)
