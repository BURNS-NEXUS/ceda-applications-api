import json
import shutil
import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart

from api.features.applications.models import Application
from api.features.tasks.models import Task, TaskAssignment

from .models import ApplicationDocument, DocumentType

TEST_MEDIA_ROOT = tempfile.mkdtemp()


def upload_file(name="registration.pdf", content=b"%PDF-1.4 test document"):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def grant_permissions(user, *codenames):
    permissions = Permission.objects.filter(
        content_type__app_label="api", codename__in=codenames
    )
    user.user_permissions.add(*permissions)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ApplicationDocumentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.user = user_model.objects.create_user(username="applicant")
        cls.other_user = user_model.objects.create_user(username="other-applicant")
        cls.reviewer = user_model.objects.create_user(username="reviewer")
        grant_permissions(
            cls.reviewer,
            "view_all_application_documents",
            "review_application_document",
        )
        cls.manager = user_model.objects.create_user(username="document-manager")
        grant_permissions(
            cls.manager,
            "manage_document_types",
            "view_all_document_types",
        )
        cls.document_admin = user_model.objects.create_user(
            username="document-admin"
        )
        grant_permissions(
            cls.document_admin,
            "view_all_application_documents",
            "manage_all_application_documents",
            "view_all_document_types",
        )
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
        Application.objects.filter(pk=cls.application.pk).update(state="verification")
        cls.application.refresh_from_db()
        cls.verification_task = Task.objects.create(
            application=cls.application,
            task_type=Task.Type.VERIFICATION,
            status=Task.Status.ASSIGNED,
        )
        TaskAssignment.objects.create(
            task=cls.verification_task,
            employee=cls.reviewer,
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
        cls.pdf_type = DocumentType.objects.create(
            name="Company Registration",
            description="Certificate of incorporation",
            allowed_file_types=["pdf"],
            is_required=True,
        )
        cls.image_type = DocumentType.objects.create(
            name="Owner ID",
            allowed_file_types=["pdf", "img"],
            is_required=True,
        )
        cls.optional_type = DocumentType.objects.create(
            name="Supporting Letter",
            allowed_file_types=["pdf"],
            is_required=False,
        )
        cls.inactive_type = DocumentType.objects.create(
            name="Old Form",
            allowed_file_types=["pdf"],
            is_active=False,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client.force_login(self.user)

    def _upload(self, document_type=None, file=None, application=None):
        document_type = document_type or self.pdf_type
        return self.client.post(
            f"/api/applications/{(application or self.application).id}/documents",
            data={
                "document_type_id": document_type.id,
                "file_description": "Uploaded document",
                "file": file or upload_file(),
            },
        )

    def _decision_url(self, document_id):
        return (
            f"/api/applications/{self.application.id}/documents/"
            f"{document_id}/decision"
        )

    def test_upload_valid_document_and_fetch_it(self):
        response = self._upload()
        self.assertEqual(response.status_code, 201, response.content)

        payload = response.json()
        self.assertEqual(payload["application_id"], self.application.id)
        self.assertEqual(payload["document_type"]["id"], self.pdf_type.id)
        self.assertEqual(payload["status"], "pending")
        self.assertEqual(payload["file_description"], "Uploaded document")
        download = payload["file"]
        response = self.client.get(download)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 test document")
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(download).status_code, 200)
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(download).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(download).status_code, 401)
        self.client.force_login(self.user)

        document = ApplicationDocument.objects.get(id=payload["id"])
        self.assertEqual(document.status, ApplicationDocument.Status.PENDING)
        self.assertTrue(document.file.name.startswith("applications/"))

        response = self.client.get(
            f"/api/applications/{self.application.id}/documents"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)

        response = self.client.get(
            f"/api/applications/{self.application.id}/documents/{document.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], document.id)

    def test_upload_rejects_disallowed_file_extension(self):
        response = self._upload(
            file=SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not allowed", response.json()["detail"])
        self.assertFalse(ApplicationDocument.objects.exists())

    def test_upload_rejects_duplicate_document_type(self):
        self.assertEqual(self._upload().status_code, 201)

        response = self._upload()
        self.assertEqual(response.status_code, 400)
        self.assertIn("already been uploaded", response.json()["detail"])
        self.assertEqual(ApplicationDocument.objects.count(), 1)

    @override_settings(MAX_DOCUMENT_FILE_SIZE=10)
    def test_upload_rejects_file_above_size_limit(self):
        response = self._upload(file=upload_file(content=b"x" * 11))
        self.assertEqual(response.status_code, 400)
        self.assertIn("File size", response.json()["detail"])
        self.assertFalse(ApplicationDocument.objects.exists())

    def test_required_document_progress(self):
        created = self._upload().json()

        response = self.client.get(
            f"/api/applications/{self.application.id}/documents/required"
        )
        self.assertEqual(response.status_code, 200)

        progress = response.json()
        document_types = {item["id"]: item for item in progress["data"]}
        self.assertIn(self.pdf_type.id, document_types)
        self.assertIn(self.image_type.id, document_types)
        self.assertIn(self.optional_type.id, document_types)
        self.assertNotIn(self.inactive_type.id, document_types)
        self.assertFalse(progress["all_required_uploaded"])
        self.assertIn(self.image_type.name, progress["missing_required"])
        self.assertTrue(document_types[self.pdf_type.id]["uploaded"])
        self.assertEqual(
            document_types[self.pdf_type.id]["document_id"], created["id"]
        )
        self.assertFalse(document_types[self.image_type.id]["uploaded"])

    def test_all_required_documents_uploaded_progress_is_true(self):
        self._upload(document_type=self.pdf_type)
        self._upload(document_type=self.image_type)

        response = self.client.get(
            f"/api/applications/{self.application.id}/documents/required"
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["all_required_uploaded"])
        self.assertEqual(response.json()["missing_required"], [])

    def test_patch_description_and_file_replacement_resets_decision(self):
        created = self._upload().json()
        document = ApplicationDocument.objects.get(id=created["id"])
        document.status = ApplicationDocument.Status.ACCEPTED
        document.decision_on = document.created_at
        document.save()

        response = self.client.patch(
            f"/api/applications/{self.application.id}/documents/{document.id}",
            data=json.dumps({"file_description": "Updated description"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["file_description"], "Updated description")
        self.assertEqual(response.json()["status"], "accepted")

        response = self.client.patch(
            f"/api/applications/{self.application.id}/documents/{document.id}",
            data=encode_multipart(
                BOUNDARY, {"file": upload_file(name="replacement.pdf")}
            ),
            content_type=MULTIPART_CONTENT,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "pending")
        self.assertEqual(response.json()["reason"], "")
        self.assertIsNone(response.json()["decision_on"])
        self.assertIsNone(response.json()["rejected_by"])

    def test_patch_rejects_invalid_replacement_file(self):
        created = self._upload().json()
        response = self.client.patch(
            f"/api/applications/{self.application.id}/documents/{created['id']}",
            data=encode_multipart(
                BOUNDARY,
                {
                    "file": SimpleUploadedFile(
                        "notes.txt", b"hello", content_type="text/plain"
                    )
                },
            ),
            content_type=MULTIPART_CONTENT,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not allowed", response.json()["detail"])

    def test_delete_document(self):
        created = self._upload().json()
        response = self.client.delete(
            f"/api/applications/{self.application.id}/documents/{created['id']}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertFalse(ApplicationDocument.objects.filter(id=created["id"]).exists())

    def test_reviewer_can_accept_document(self):
        created = self._upload().json()
        self.client.force_login(self.reviewer)

        response = self.client.post(
            self._decision_url(created["id"]),
            data={"status": "accepted"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["status"], "accepted")
        self.assertIsNone(payload["rejected_by"])
        self.assertIsNotNone(payload["decision_on"])

    def test_reviewer_can_reject_document_with_reason(self):
        created = self._upload().json()
        self.client.force_login(self.reviewer)

        response = self.client.post(
            self._decision_url(created["id"]),
            data={"status": "rejected", "reason": "Document is unreadable"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["status"], "rejected")
        self.assertEqual(payload["reason"], "Document is unreadable")
        self.assertEqual(payload["rejected_by"]["id"], self.reviewer.id)
        self.assertIsNotNone(payload["decision_on"])

    def test_reject_requires_reason(self):
        created = self._upload().json()
        self.client.force_login(self.reviewer)

        response = self.client.post(
            self._decision_url(created["id"]),
            data={"status": "rejected"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("reason is required", response.json()["detail"])

    def test_reviewer_can_redo_decision(self):
        created = self._upload().json()
        self.client.force_login(self.reviewer)
        url = (
            f"/api/applications/{self.application.id}/documents/"
            f"{created['id']}/decision"
        )

        self.client.post(
            url,
            data={"status": "rejected", "reason": "Blurry scan"},
            content_type="application/json",
        )
        response = self.client.post(
            url,
            data={"status": "accepted"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["status"], "accepted")
        self.assertEqual(payload["reason"], "")
        self.assertIsNone(payload["rejected_by"])
        self.assertIsNotNone(payload["decision_on"])

    def test_reviewer_can_list_any_applications_documents(self):
        self._upload()
        self.client.force_login(self.reviewer)

        response = self.client.get(
            f"/api/applications/{self.application.id}/documents"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)

    def test_applicant_cannot_decide_document(self):
        created = self._upload().json()
        response = self.client.post(
            self._decision_url(created["id"]),
            data={"status": "accepted"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_other_applicants_documents_are_not_accessible(self):
        document = ApplicationDocument.objects.create(
            application=self.other_application,
            document_type=self.pdf_type,
            file=upload_file(),
        )

        response = self.client.get(
            f"/api/applications/{self.other_application.id}/documents"
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            f"/api/applications/{self.application.id}/documents/{document.id}"
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            f"/api/applications/{self.other_application.id}/documents",
            data={
                "document_type_id": self.image_type.id,
                "file": upload_file(name="id.pdf"),
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_document_is_scoped_to_application(self):
        created = self._upload().json()
        response = self.client.get(
            f"/api/applications/{self.other_application.id}/documents/{created['id']}"
        )
        self.assertEqual(response.status_code, 404)

    def test_document_type_catalog_hides_inactive_types(self):
        response = self.client.get("/api/document-types")
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.json()}
        self.assertIn(self.pdf_type.id, ids)
        self.assertNotIn(self.inactive_type.id, ids)

        response = self.client.get(
            "/api/document-types", {"include_inactive": "true"}
        )
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.manager)
        response = self.client.get(
            "/api/document-types", {"include_inactive": "true"}
        )
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.json()}
        self.assertIn(self.inactive_type.id, ids)

    def test_applicant_cannot_manage_document_types(self):
        payload = {
            "name": "Tax Clearance",
            "allowed_file_types": ["pdf"],
        }
        self.assertEqual(
            self.client.post(
                "/api/document-types",
                data=payload,
                content_type="application/json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/document-types/{self.pdf_type.id}",
                data={"is_required": False},
                content_type="application/json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/document-types/{self.optional_type.id}"
            ).status_code,
            403,
        )
        self.assertFalse(DocumentType.objects.filter(name="Tax Clearance").exists())

    def test_manager_can_create_update_and_delete_document_type(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            "/api/document-types",
            data={
                "name": "Tax Clearance",
                "description": "Valid tax clearance certificate",
                "allowed_file_types": ["pdf"],
                "is_required": True,
                "is_active": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        created = response.json()
        self.assertEqual(created["name"], "Tax Clearance")
        self.assertTrue(created["is_required"])

        response = self.client.patch(
            f"/api/document-types/{created['id']}",
            data={"is_required": False, "is_active": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["is_required"])
        self.assertFalse(response.json()["is_active"])

        response = self.client.delete(f"/api/document-types/{created['id']}")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(DocumentType.objects.filter(id=created["id"]).exists())

    def test_document_type_creation_validates_input(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            "/api/document-types",
            data={
                "name": self.pdf_type.name,
                "allowed_file_types": ["pdf"],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/document-types",
            data={"name": "Unsupported", "allowed_file_types": ["docx"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid file type", response.json()["detail"])

    def test_document_type_with_documents_cannot_be_deleted(self):
        self._upload()
        self.client.force_login(self.manager)

        response = self.client.delete(f"/api/document-types/{self.pdf_type.id}")
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot be deleted", response.json()["detail"])
        self.assertTrue(DocumentType.objects.filter(id=self.pdf_type.id).exists())

        response = self.client.patch(
            f"/api/document-types/{self.pdf_type.id}",
            data={"is_active": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["is_active"])

    def test_permissions_work_without_staff_status_or_groups(self):
        self.assertFalse(self.reviewer.is_staff)
        self.assertFalse(self.reviewer.groups.exists())

        created = self._upload().json()
        self.client.force_login(self.reviewer)
        response = self.client.post(
            self._decision_url(created["id"]),
            data={"status": "accepted"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_manage_all_permission_allows_cross_application_access(self):
        self.client.force_login(self.document_admin)

        response = self._upload(application=self.other_application)
        self.assertEqual(response.status_code, 201, response.content)

        response = self.client.get(
            f"/api/applications/{self.other_application.id}/documents"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)

    def test_anonymous_users_cannot_access_documents(self):
        self.client.logout()
        response = self.client.get(
            f"/api/applications/{self.application.id}/documents"
        )
        self.assertEqual(response.status_code, 401)
