from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import localdate

from api.features.applications.models import Application, ProgrammeCall
from api.features.documents.models import DocumentType
from api.features.personal_details.models import (
    Address,
    Contact,
    Employment,
    PersonalDetails,
)

CUSTOMER = "customer@ceda.local"

OPEN_CALL_TITLE = "CEDA Innovation Growth Fund — 2026 Round 1"
DRAFT_CALL_TITLE = "Youth Agri-Technology Challenge 2026"

DOCUMENT_TYPES = (
    {
        "name": "Company registration certificate",
        "description": "Certificate issued by CIPA.",
        "allowed_file_types": ["pdf"],
        "application_type": "company",
    },
    {
        "name": "Proof of identification",
        "description": "National identity card or passport.",
        "allowed_file_types": ["pdf", "img"],
        "application_type": "all",
    },
    {
        "name": "Latest financial statements",
        "description": "Audited or management accounts for the most recent financial year.",
        "allowed_file_types": ["pdf"],
        "application_type": "company",
    },
    {
        "name": "Project brief",
        "description": "Description of the innovation, market and intended use of funds.",
        "allowed_file_types": ["pdf"],
        "application_type": "all",
    },
)

APPLICATIONS = (
    {
        "project_title": "Solar-powered irrigation system",
        "company_no": "BW-DEMO-001",
        "incorporation_date": date(2021, 3, 12),
        "contact_person": "Thabo Disele",
        "telephone": "+267 71 234 567",
        "business_nature": "Renewable energy and irrigation",
        "business_location": "Gaborone, Botswana",
        "loan_amount": 450000,
        "email": CUSTOMER,
        "application_type": "company",
        "has_current_loan_with_other": False,
        "has_past_loan_with_other": True,
    },
    {
        "project_title": "Smart livestock health monitoring",
        "company_no": "BW-DEMO-002",
        "incorporation_date": date(2022, 7, 4),
        "contact_person": "Thabo Disele",
        "telephone": "+267 71 234 567",
        "business_nature": "Agricultural technology",
        "business_location": "Francistown, Botswana",
        "loan_amount": 280000,
        "email": CUSTOMER,
        "application_type": "company",
        "has_current_loan_with_other": False,
        "has_past_loan_with_other": False,
    },
    {
        "project_title": "Solar cold storage for fresh produce",
        "company_no": "BW-DEMO-003",
        "incorporation_date": date(2023, 1, 20),
        "contact_person": "Thabo Disele",
        "telephone": "+267 71 234 567",
        "business_nature": "Renewable energy and food logistics",
        "business_location": "Lobatse, Botswana",
        "loan_amount": 620000,
        "email": CUSTOMER,
        "application_type": "company",
        "has_current_loan_with_other": True,
        "has_past_loan_with_other": False,
    },
)


class Command(BaseCommand):
    help = "Seed a published programme call and customer applications for the portal demo."

    @transaction.atomic
    def handle(self, *args, **options):
        owner = get_user_model().objects.filter(username=CUSTOMER).first()
        if owner is None:
            raise CommandError(f"Create the {CUSTOMER} user before seeding the portal.")

        today = localdate()
        open_call, _ = ProgrammeCall.objects.get_or_create(
            title=OPEN_CALL_TITLE,
            defaults={
                "description": "Concessional financing and business support for Botswana-owned innovations with commercial potential.",
                "eligibility": "Registered Botswana companies or individual innovators aged 18 and above.",
                "required_documents": "Company registration certificate, ID copies, recent financial statements and a project brief.",
                "opens_on": today - timedelta(days=14),
                "closes_on": today + timedelta(days=45),
                "published": True,
                "has_brief": False,
            },
        )
        ProgrammeCall.objects.get_or_create(
            title=DRAFT_CALL_TITLE,
            defaults={
                "description": "Pilot funding for youth-led agricultural technology solutions.",
                "eligibility": "Applicants aged 18 to 35 with a registered venture.",
                "required_documents": "ID copy, company registration and a concept note.",
                "opens_on": today + timedelta(days=7),
                "closes_on": today + timedelta(days=60),
                "published": False,
                "has_brief": False,
            },
        )

        for item in DOCUMENT_TYPES:
            DocumentType.objects.get_or_create(name=item["name"], defaults=item)

        created = 0
        for item in APPLICATIONS:
            application, is_new = Application.objects.get_or_create(
                programme_call=open_call,
                owner=owner,
                company_no=item["company_no"],
                defaults=item,
            )
            if not is_new:
                continue
            created += 1
            PersonalDetails.objects.get_or_create(
                application=application,
                defaults={
                    "title": "Mr",
                    "surname": "Disele",
                    "other_names": "Thabo",
                    "id_number": "BW-1234567",
                    "date_of_birth": date(1990, 5, 14),
                    "marital_status": "Single",
                },
            )
            Address.objects.get_or_create(
                application=application,
                defaults={
                    "postal_address": "P.O. Box 1234, Gaborone",
                    "physical_address": "Plot 42, Industrial Area",
                    "duration_of_stay": "5 years",
                },
            )
            Contact.objects.get_or_create(
                application=application,
                defaults={
                    "contact_type": "Cell Phone",
                    "contact_value": item["telephone"],
                    "email": item["email"],
                },
            )
            Employment.objects.get_or_create(
                application=application,
                defaults={
                    "employer_name": "Disele Innovations (Pty) Ltd",
                    "employer_address": "Gaborone, Botswana",
                    "job_title": "Director",
                    "salary_per_month": 25000,
                    "training_experience": "Renewable energy systems and project management.",
                    "project_description": item["business_nature"],
                    "ever_applied_for_loan": False,
                    "loan_amount_requested": item["loan_amount"],
                },
            )

        self.stdout.write(
            f"Programme calls: {ProgrammeCall.objects.count()}; "
            f"applications: {Application.objects.count()} (created {created}); "
            f"customer applications: {Application.objects.filter(owner=owner).count()}; "
            f"document types: {DocumentType.objects.count()}."
        )
