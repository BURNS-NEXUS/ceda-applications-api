import random
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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

my_word_list = [
    "Danish",
    "Cheesecake",
    "Sugar",
    "Lollipop",
    "Wafer",
    "Gummies",
    "Sesame",
    "Jelly",
    "Beans",
    "Pie",
    "Bar",
    "Ice",
    "Oat",
]


def gen_random_word(word_count):
    return " ".join(random.choice(my_word_list) for _ in range(word_count))


def gen_random_phone():
    return f"+{random.randint(100000000, 999999999)}"


def gen_random_application_type():
    return random.choice(["individual", "company"])


def gen_random_email():
    domains = ["ceda.local", "example.com", "test.com"]
    return f"customer{random.randint(1, 100)}@{random.choice(domains)}"


def gen_random_date(start_year=1960, end_year=2005):
    return date(
        random.randint(start_year, end_year),
        random.randint(1, 12),
        random.randint(1, 28),
    )


class Command(BaseCommand):
    help = "Seed applications and their related records"

    @transaction.atomic
    def handle(self, *args, **options):
        users = list(get_user_model().objects.all())
        if not users:
            raise CommandError("Create at least one user before seeding applications.")

        criterion, _ = EvaluationCriterion.objects.get_or_create(
            name="Overall application assessment",
            defaults={
                "description": "Seeded overall assessment of the application",
                "maximum_score": 100,
            },
        )

        for _ in range(10):
            application = Application.objects.create(
                owner=random.choice(users),
                project_title=gen_random_word(3),
                company_no=f"BW{random.randint(100, 999)}",
                incorporation_date=f"202{random.randint(0, 5)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                contact_person=gen_random_word(2),
                telephone=gen_random_phone(),
                business_nature=gen_random_word(6),
                business_location=f"P.O Box \n {gen_random_word(1)}",
                loan_amount=str(random.randint(100000, 1000000)),
                email=gen_random_email(),
                application_type=gen_random_application_type(),
                has_current_loan_with_other=random.choice([True, False]),
                has_past_loan_with_other=random.choice([True, False]),
            )
            PersonalDetails.objects.create(
                application=application,
                title=random.choice(["Mr", "Mrs", "Ms", "Dr"]),
                surname=gen_random_word(1),
                other_names=gen_random_word(2),
                id_number=str(random.randint(100000000, 999999999)),
                date_of_birth=gen_random_date(),
                marital_status=random.choice(["Single", "Married", "Divorced"]),
            )
            Address.objects.create(
                application=application,
                postal_address=f"P.O Box {random.randint(1, 9999)}",
                physical_address=f"Plot {random.randint(1, 999)}, {gen_random_word(1)}",
                duration_of_stay=f"{random.randint(1, 20)} years",
            )
            Contact.objects.create(
                application=application,
                contact_type="Cell Phone",
                contact_value=gen_random_phone(),
                email=gen_random_email(),
            )
            Employment.objects.create(
                application=application,
                employer_name=f"{gen_random_word(2)} (Pty) Ltd",
                employer_address=gen_random_word(3),
                job_title=random.choice(["Director", "Manager", "Owner", "Supervisor"]),
                salary_per_month=random.randint(10000, 80000),
                training_experience=gen_random_word(8),
                project_description=application.business_nature,
                ever_applied_for_loan=random.choice([True, False]),
                loan_amount_requested=application.loan_amount,
            )

            company = CorporateDetails.objects.create(
                application=application,
                name_of_company=f"{gen_random_word(2)} Holdings",
                date_of_incorporation=gen_random_date(2000, 2025),
                nature_of_company=application.business_nature,
            )
            authorized_capital = random.randint(100000, 1000000)
            issued_capital = random.randint(50000, authorized_capital)
            for _ in range(random.randint(2, 6)):
                ShareHolders.objects.create(
                    application=application,
                    name=gen_random_word(2),
                    dob=gen_random_date(),
                    nationality="Motswana",
                    id_number=str(random.randint(100000000, 999999999)),
                    position=random.choice(
                        ["Director", "Managing Director", "Shareholder"]
                    ),
                    company=company,
                    total_authorized_share_capital=authorized_capital,
                    total_issued_share_capital=issued_capital,
                )

            for _ in range(random.randint(1, 3)):
                loan_amount = random.randint(50000, 500000)
                Loans.objects.create(
                    application=application,
                    institution_name=f"{gen_random_word(1)} Bank",
                    account_number=str(random.randint(100000000, 999999999)),
                    loan_amount=loan_amount,
                    repayment_amount=random.randint(1000, 10000),
                    repayment_period=random.choice([12, 24, 36, 48, 60]),
                    amount_outstanding=random.randint(0, loan_amount),
                    is_past_loan=random.choice([True, False]),
                )

            for _ in range(2):
                References.objects.create(
                    application=application,
                    name=gen_random_word(2),
                    postal_address=f"P.O Box {random.randint(1, 9999)}",
                    cell_phone=gen_random_phone(),
                )
                NextOfKin.objects.create(
                    application=application,
                    name=gen_random_word(2),
                    relationship=random.choice(
                        ["Spouse", "Sibling", "Parent", "Child"]
                    ),
                    id_number=str(random.randint(100000000, 999999999)),
                    postal_address=f"P.O Box {random.randint(1, 9999)}",
                    physical_address=f"Plot {random.randint(1, 999)}",
                    cell_phone=gen_random_phone(),
                )

            ReferencesCommercialBankers.objects.create(
                application=application,
                bank_name=f"{gen_random_word(1)} Bank",
                account_number=str(random.randint(100000000, 999999999)),
                address=gen_random_word(3),
                branch=random.choice(["Gaborone", "Francistown", "Lobatse"]),
                cell_phone=gen_random_phone(),
                accountants_auditor=gen_random_word(3),
                company_name=f"{gen_random_word(2)} Auditors",
                contact_person=gen_random_word(2),
                contact_person_address=gen_random_word(3),
                contact_person_cell_phone=gen_random_phone(),
            )

            evaluation = Evaluation.objects.create(
                application=application,
                evaluator=random.choice(users),
                comments=gen_random_word(6),
            )
            EvaluationScore.objects.create(
                evaluation=evaluation,
                criterion=criterion,
                score=random.randint(1, criterion.maximum_score),
                comments=gen_random_word(5),
            )

            self.stdout.write(
                self.style.SUCCESS(f"Created application '{application.project_title}'")
            )
