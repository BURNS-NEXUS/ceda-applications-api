from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

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
    import random

    return " ".join(random.choice(my_word_list) for _ in range(word_count))


def gen_random_phone():
    import random

    return f"+{random.randint(100000000, 999999999)}"


def gen_random_email():
    import random

    domains = ["ceda.local", "example.com", "test.com"]
    return f"customer{random.randint(1, 100)}@{random.choice(domains)}"


class Command(BaseCommand):
    help = "Seed  applications"

    @transaction.atomic
    def handle(self, *args, **options):
        import random

        from api.features.applications.models import Application

        users = get_user_model().objects.all()
        for _ in range(10):
            application = Application.objects.create(
                owner=random.choice(users),
                project_title=gen_random_word(3),
                company_no=f"BW{random.randint(100, 999)}",
                incorporation_date=f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                contact_person=gen_random_word(2),
                telephone=gen_random_phone(),
                business_nature=gen_random_word(2),
                business_location=f"P.O Box \n {gen_random_word(1)}",
                loan_amount=str(random.randint(100000, 1000000)),
                email=gen_random_email(),
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created application '{application.project_title}'")
            )
