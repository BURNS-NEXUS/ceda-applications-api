from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils.timezone import localdate

from .models import ProgrammeCall


class ProgrammeFlowTests(TestCase):
    def test_publication_brief_and_application(self):
        users = get_user_model().objects
        admin = users.create_superuser("programme-admin", "admin@example.test", "test")
        innovator = users.create_user("innovator")
        self.client.force_login(admin)
        today = localdate()
        fields = dict(title="Water", description="Water projects", eligibility="Local innovators",
                      required_documents="Company profile", opens_on=today, closes_on=today,
                      brief=SimpleUploadedFile("brief.pdf", b"%PDF-1.4 sample"))
        created = self.client.post("/api/programmes/", fields)
        self.assertEqual(created.status_code, 201, created.content)
        call_id = created.json()["id"]
        path = f"/api/programmes/{call_id}"
        self.client.force_login(innovator)
        self.assertEqual(self.client.get("/api/programmes/").json(), [])
        self.assertEqual(self.client.get(path + "/brief").status_code, 404)
        self.assertEqual(self.client.post(path + "/publish").status_code, 403)
        self.client.force_login(admin)
        self.assertEqual(self.client.post(path + "/publish").json()["status"], "open")
        self.client.force_login(innovator)
        self.assertEqual(self.client.get("/api/programmes/").json()[0]["id"], call_id)
        self.assertEqual(self.client.get(path + "/brief").content, b"%PDF-1.4 sample")
        data = dict(project_title="Pilot", company_no="S", incorporation_date=today.isoformat(),
                    contact_person="Applicant", telephone="1", business_nature="Water",
                    business_location="City", loan_amount=100, email="a@example.test",
                    has_current_loan_with_other=False, has_past_loan_with_other=False,
                    application_type="company", programme_call_id=call_id)
        draft = self.client.post("/api/applications/", data, content_type="application/json")
        self.assertEqual(draft.status_code, 201, draft.content)
        self.assertEqual(draft.json()["programme_call_id"], call_id)
        self.assertEqual(self.client.get(path + "/applications").status_code, 403)
        ProgrammeCall.objects.filter(pk=call_id).update(closes_on=today - timedelta(days=1))
        self.assertEqual(self.client.post("/api/applications/", data, content_type="application/json").status_code, 409)
        self.assertEqual(self.client.post(f"/api/applications/{draft.json()['id']}/wf/submit").status_code, 409)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(path + "/applications").json()[0]["id"], draft.json()["id"])
