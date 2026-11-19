from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from api.features.applications.models import Application
from api.models import Evaluation, EvaluationCriterion, EvaluationScore


class EvaluationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.evaluator = user_model.objects.create_user(username="evaluator")
        cls.owner = user_model.objects.create_user(username="owner")
        cls.application = Application.objects.create(
            owner=cls.owner,
            project_title="Test application",
            company_no="CO-1",
            incorporation_date=date(2025, 1, 1),
            contact_person="Test Person",
            telephone="71000000",
            business_nature="Retail",
            business_location="Gaborone",
            loan_amount="100000.00",
            email="owner@example.com",
        )
        cls.criterion = EvaluationCriterion.objects.create(
            name="Financial viability",
            maximum_score=10,
        )

    def test_each_evaluator_can_evaluate_an_application_once(self):
        Evaluation.objects.create(
            application=self.application,
            evaluator=self.evaluator,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Evaluation.objects.create(
                application=self.application,
                evaluator=self.evaluator,
            )

    def test_each_criterion_can_be_scored_once_per_evaluation(self):
        evaluation = Evaluation.objects.create(
            application=self.application,
            evaluator=self.evaluator,
        )
        EvaluationScore.objects.create(
            evaluation=evaluation,
            criterion=self.criterion,
            score=8,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            EvaluationScore.objects.create(
                evaluation=evaluation,
                criterion=self.criterion,
                score=9,
            )

    def test_score_cannot_exceed_criterion_maximum(self):
        evaluation = Evaluation.objects.create(
            application=self.application,
            evaluator=self.evaluator,
        )
        result = EvaluationScore(
            evaluation=evaluation,
            criterion=self.criterion,
            score=11,
        )

        with self.assertRaises(ValidationError):
            result.full_clean()

    def test_user_exposes_its_evaluations(self):
        evaluation = Evaluation.objects.create(
            application=self.application,
            evaluator=self.evaluator,
        )

        self.assertQuerySetEqual(
            self.evaluator.evaluations.all(),
            [evaluation],
        )
