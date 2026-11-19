from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from api.features.applications.models import Application

from .models import NextOfKin, References, ReferencesCommercialBankers


class ReferenceCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="reference-applicant")
        cls.other_user = user_model.objects.create_user(
            username="other-reference-applicant"
        )
        cls.application = Application.objects.create(
            owner=cls.user,
            project_title="Reference project",
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
            project_title="Other reference project",
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

    def test_create_list_update_and_delete_all_reference_types(self):
        resources = (
            (
                "references",
                References,
                {
                    "name": "Referee One",
                    "postal_address": "Private Bag 1",
                    "cell_phone": "71000000",
                },
                {"cell_phone": "73000000"},
            ),
            (
                "commercial-bankers",
                ReferencesCommercialBankers,
                {
                    "bank_name": "Example Bank",
                    "account_number": "123456789",
                    "address": "Main Street",
                    "branch": "Gaborone",
                    "cell_phone": "3111111",
                    "accountants_auditor": "Auditor One",
                    "company_name": "Example Auditors",
                    "contact_person": "Auditor Contact",
                    "contact_person_address": "Plot 10",
                    "contact_person_cell_phone": "72000000",
                },
                {"branch": "Mogoditshane"},
            ),
            (
                "next-of-kin",
                NextOfKin,
                {
                    "name": "Next Person",
                    "relationship": "Sibling",
                    "id_number": "987654321",
                    "postal_address": "Private Bag 2",
                    "physical_address": "Plot 20",
                    "cell_phone": "74000000",
                },
                {"relationship": "Spouse"},
            ),
        )

        for path, model, values, changes in resources:
            with self.subTest(path=path):
                response = self.client.post(
                    f"/api/{path}",
                    data={"application_id": self.application.id, **values},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 201, response.content)
                record_id = response.json()["id"]
                self.assertEqual(
                    model.objects.get(id=record_id).application_id,
                    self.application.id,
                )
                response = self.client.get(
                    f"/api/{path}", {"application_id": self.application.id}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["total"], 1)

                response = self.client.patch(
                    f"/api/{path}/{record_id}",
                    data={"application_id": self.application.id, **changes},
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 200, response.content)
                for field, value in changes.items():
                    self.assertEqual(response.json()[field], value)

                self.assertEqual(
                    self.client.delete(f"/api/{path}/{record_id}").status_code, 200
                )
                self.assertFalse(model.objects.filter(id=record_id).exists())

    def test_application_id_is_required_and_must_belong_to_user(self):
        payload = {
            "name": "Referee One",
            "postal_address": "Private Bag 1",
            "cell_phone": "71000000",
        }
        self.assertEqual(
            self.client.post(
                "/api/references", data=payload, content_type="application/json"
            ).status_code,
            422,
        )
        response = self.client.post(
            "/api/references",
            data={"application_id": self.other_application.id, **payload},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(References.objects.exists())

    def test_other_users_records_are_not_accessible(self):
        reference = References.objects.create(
            application=self.other_application,
            name="Other Referee",
            postal_address="Other postal address",
            cell_phone="72000000",
        )
        self.assertEqual(self.client.get("/api/references").json()["total"], 0)
        self.assertEqual(
            self.client.get(f"/api/references/{reference.id}").status_code, 404
        )
        response = self.client.patch(
            f"/api/references/{reference.id}",
            data={
                "application_id": self.application.id,
                "name": "Changed",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
