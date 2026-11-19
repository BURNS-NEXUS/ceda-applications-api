from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from api.features.applications.models import Application

from .models import Loans


class LoanCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="loan-applicant")
        cls.other_user = user_model.objects.create_user(
            username="other-loan-applicant"
        )
        cls.application = Application.objects.create(
            owner=cls.user,
            project_title="Loan project",
            company_no="CO-123",
            incorporation_date=date(2025, 1, 1),
            contact_person="Applicant",
            telephone="71000000",
            business_nature="Retail",
            business_location="Gaborone",
            loan_amount="100000.00",
            email="applicant@example.com",
        )
        cls.other_application = Application.objects.create(
            owner=cls.other_user,
            project_title="Other loan project",
            company_no="CO-456",
            incorporation_date=date(2025, 1, 1),
            contact_person="Other",
            telephone="72000000",
            business_nature="Manufacturing",
            business_location="Francistown",
            loan_amount="50000.00",
            email="other@example.com",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_loan_crud(self):
        payload = {
            "application_id": self.application.id,
            "institution_name": "Example Bank",
            "account_number": "123456789",
            "loan_amount": "75000.00",
            "repayment_amount": "2500.00",
            "repayment_period": 36,
            "amount_outstanding": "50000.00",
            "is_past_loan": False,
        }
        response = self.client.post(
            "/api/loans", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        record_id = response.json()["id"]
        self.assertEqual(response.json()["application_id"], self.application.id)

        response = self.client.get(
            "/api/loans", {"application_id": self.application.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)

        response = self.client.patch(
            f"/api/loans/{record_id}",
            data={
                "application_id": self.application.id,
                "amount_outstanding": "40000.00",
                "is_past_loan": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["amount_outstanding"], "40000.00")
        self.assertTrue(response.json()["is_past_loan"])

        self.assertEqual(self.client.delete(f"/api/loans/{record_id}").status_code, 200)
        self.assertFalse(Loans.objects.filter(id=record_id).exists())

    def test_application_id_is_required_and_must_belong_to_user(self):
        payload = {
            "institution_name": "Example Bank",
            "account_number": "123456789",
            "loan_amount": "75000.00",
            "repayment_amount": "2500.00",
            "repayment_period": 36,
            "amount_outstanding": "50000.00",
            "is_past_loan": False,
        }
        self.assertEqual(
            self.client.post(
                "/api/loans", data=payload, content_type="application/json"
            ).status_code,
            422,
        )
        response = self.client.post(
            "/api/loans",
            data={"application_id": self.other_application.id, **payload},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Loans.objects.exists())

    def test_invalid_financial_values_are_rejected(self):
        payload = {
            "application_id": self.application.id,
            "institution_name": "Example Bank",
            "account_number": "123456789",
            "loan_amount": "75000.00",
            "repayment_amount": "2500.00",
            "repayment_period": 0,
            "amount_outstanding": "-1.00",
            "is_past_loan": False,
        }
        response = self.client.post(
            "/api/loans", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(Loans.objects.exists())

    def test_other_users_loans_are_not_accessible(self):
        loan = Loans.objects.create(
            application=self.other_application,
            institution_name="Other Bank",
            account_number="987654321",
            loan_amount="50000.00",
            repayment_amount="2000.00",
            repayment_period=24,
            amount_outstanding="30000.00",
            is_past_loan=False,
        )
        self.assertEqual(self.client.get("/api/loans").json()["total"], 0)
        self.assertEqual(self.client.get(f"/api/loans/{loan.id}").status_code, 404)
        response = self.client.patch(
            f"/api/loans/{loan.id}",
            data={
                "application_id": self.application.id,
                "amount_outstanding": "25000.00",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
