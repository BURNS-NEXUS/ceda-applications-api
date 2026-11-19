from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from api.features.applications.models import Application

from .models import Address, Contact, Employment, PersonalDetails


class ApplicantDetailsCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="applicant")
        cls.other_user = user_model.objects.create_user(username="other-applicant")
        cls.application = Application.objects.create(
            owner=cls.user,
            project_title="Applicant project",
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
            project_title="Other project",
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

    def test_create_list_update_and_delete_all_resources(self):
        resources = (
            (
                "personal-details",
                PersonalDetails,
                {
                    "title": "Ms",
                    "surname": "Molefe",
                    "other_names": "Neo",
                    "id_number": "123456789",
                    "date_of_birth": "1990-05-10",
                    "marital_status": "Single",
                },
                {"marital_status": "Married"},
            ),
            (
                "address",
                Address,
                {
                    "postal_address": "Private Bag 1",
                    "physical_address": "Plot 10",
                    "duration_of_stay": "5 years",
                },
                {"physical_address": "Plot 11"},
            ),
            (
                "contact",
                Contact,
                {
                    "contact_type": "Cell Phone",
                    "contact_value": "71000000",
                    "email": "neo@example.com",
                },
                {"contact_value": "73000000"},
            ),
            (
                "employment",
                Employment,
                {
                    "employer_name": "Example Company",
                    "employer_address": "Gaborone",
                    "job_title": "Manager",
                    "salary_per_month": "15000.00",
                    "training_experience": "Management",
                    "project_description": "Expand retail shop",
                    "ever_applied_for_loan": False,
                    "loan_amount_requested": "100000.00",
                },
                {"job_title": "Director"},
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

                response = self.client.delete(f"/api/{path}/{record_id}")
                self.assertEqual(response.status_code, 200)
                self.assertFalse(model.objects.filter(id=record_id).exists())

    def test_application_id_is_required_and_must_belong_to_user(self):
        payload = {
            "postal_address": "Private Bag 1",
            "physical_address": "Plot 10",
            "duration_of_stay": "5 years",
        }
        self.assertEqual(
            self.client.post(
                "/api/address",
                data=payload,
                content_type="application/json",
            ).status_code,
            422,
        )
        response = self.client.post(
            "/api/address",
            data={"application_id": self.other_application.id, **payload},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Address.objects.exists())

    def test_other_users_records_are_not_accessible(self):
        address = Address.objects.create(
            application=self.other_application,
            postal_address="Other postal",
            physical_address="Other physical",
            duration_of_stay="1 year",
        )

        self.assertEqual(self.client.get("/api/address").json()["total"], 0)
        self.assertEqual(self.client.get(f"/api/address/{address.id}").status_code, 404)
        response = self.client.patch(
            f"/api/address/{address.id}",
            data={
                "application_id": self.application.id,
                "postal_address": "Changed",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
