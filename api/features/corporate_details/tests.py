from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from api.features.applications.models import Application

from .models import CorporateDetails, ShareHolders


class CorporateDetailsCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="company-owner")
        cls.other_user = user_model.objects.create_user(username="other-company-owner")
        cls.application = Application.objects.create(
            owner=cls.user,
            project_title="Company project",
            company_no="CO-123",
            incorporation_date=date(2025, 1, 1),
            contact_person="Owner",
            telephone="71000000",
            business_nature="Retail",
            business_location="Gaborone",
            loan_amount="100000.00",
            email="owner@example.com",
        )
        cls.other_application = Application.objects.create(
            owner=cls.other_user,
            project_title="Other company project",
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

    def test_corporate_details_crud(self):
        payload = {
            "application_id": self.application.id,
            "name_of_company": "Example Holdings",
            "date_of_incorporation": "2020-01-10",
            "nature_of_company": "Retail",
        }
        response = self.client.post(
            "/api/corporate-details", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        record_id = response.json()["id"]
        self.assertEqual(response.json()["application_id"], self.application.id)

        self.assertEqual(
            self.client.get(
                "/api/corporate-details",
                {"application_id": self.application.id},
            ).json()["total"],
            1,
        )
        response = self.client.patch(
            f"/api/corporate-details/{record_id}",
            data={
                "application_id": self.application.id,
                "nature_of_company": "Manufacturing",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["nature_of_company"], "Manufacturing")
        self.assertEqual(
            self.client.delete(f"/api/corporate-details/{record_id}").status_code,
            200,
        )
        self.assertFalse(CorporateDetails.objects.filter(id=record_id).exists())

    def test_shareholder_crud_and_company_application_consistency(self):
        company = CorporateDetails.objects.create(
            application=self.application,
            name_of_company="Example Holdings",
            date_of_incorporation=date(2020, 1, 10),
            nature_of_company="Retail",
        )
        payload = {
            "application_id": self.application.id,
            "company_id": company.id,
            "name": "Neo Molefe",
            "dob": "1990-05-10",
            "nationality": "Motswana",
            "id_number": "123456789",
            "position": "Director",
            "total_authorized_share_capital": "100000.00",
            "total_issued_share_capital": "50000.00",
        }
        response = self.client.post(
            "/api/shareholders", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        record_id = response.json()["id"]
        self.assertEqual(response.json()["company_id"], company.id)

        response = self.client.patch(
            f"/api/shareholders/{record_id}",
            data={
                "application_id": self.application.id,
                "position": "Managing Director",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["position"], "Managing Director")

        other_company = CorporateDetails.objects.create(
            application=self.other_application,
            name_of_company="Other Holdings",
            date_of_incorporation=date(2021, 1, 10),
            nature_of_company="Manufacturing",
        )
        response = self.client.patch(
            f"/api/shareholders/{record_id}",
            data={
                "application_id": self.application.id,
                "company_id": other_company.id,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.client.delete(f"/api/shareholders/{record_id}").status_code, 200
        )
        self.assertFalse(ShareHolders.objects.filter(id=record_id).exists())

    def test_application_id_is_required_and_other_users_are_hidden(self):
        response = self.client.post(
            "/api/corporate-details",
            data={
                "name_of_company": "Example Holdings",
                "date_of_incorporation": "2020-01-10",
                "nature_of_company": "Retail",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)

        company = CorporateDetails.objects.create(
            application=self.other_application,
            name_of_company="Other Holdings",
            date_of_incorporation=date(2021, 1, 10),
            nature_of_company="Manufacturing",
        )
        self.assertEqual(self.client.get("/api/corporate-details").json()["total"], 0)
        self.assertEqual(
            self.client.get(f"/api/corporate-details/{company.id}").status_code,
            404,
        )
        response = self.client.post(
            "/api/corporate-details",
            data={
                "application_id": self.other_application.id,
                "name_of_company": "Hidden Holdings",
                "date_of_incorporation": "2022-01-10",
                "nature_of_company": "Services",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
