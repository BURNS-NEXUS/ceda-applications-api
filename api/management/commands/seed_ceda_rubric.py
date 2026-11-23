"""Install the CEDA/BIA evaluator rubric.

The rubric is the assessment specification used by CEDA evaluators: six
categories, each scored on a whole-number 1-5 scale with a comment. Criteria
live in the database so the portal never hardcodes the published rubric; this
command keeps that database record canonical and idempotent.

Legacy criteria are deactivated rather than deleted because existing scores
reference them with ``on_delete=PROTECT``.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from api.features.scoring.models import ScoringCriterion

CEDA_RUBRIC = (
    {
        "name": "Strategic Alignment",
        "description": "Supports CEDA’s mission and Botswana’s Vision 2036.",
    },
    {
        "name": "Innovation & Originality",
        "description": "Significant improvement or new concept using emerging technology.",
    },
    {
        "name": "Impact Potential",
        "description": "Job creation, youth/women empowerment, and environmental sustainability.",
    },
    {
        "name": "Feasibility & Viability",
        "description": "Technically sound, with resources available.",
    },
    {
        "name": "Scalability & Sustainability",
        "description": "Replicable, financially sustainable, and clear growth plans.",
    },
    {
        "name": "Implementation Capacity",
        "description": "Team capability, governance, and relevant experience and leadership.",
    },
)

RUBRIC_NAMES = {entry["name"] for entry in CEDA_RUBRIC}


class Command(BaseCommand):
    help = "Seed and activate the six CEDA/BIA evaluation criteria (1-5 scale)."

    @transaction.atomic
    def handle(self, *args, **options):
        for order, entry in enumerate(CEDA_RUBRIC, start=1):
            criterion, created = ScoringCriterion.objects.get_or_create(
                name=entry["name"],
                defaults={
                    "description": entry["description"],
                    "weight": Decimal("1.00"),
                    "max_score": Decimal("5.00"),
                    "score_type": ScoringCriterion.ScoreType.NUMERIC,
                    "is_required": True,
                    "is_active": True,
                    "order": order,
                },
            )
            criterion.description = entry["description"]
            criterion.weight = Decimal("1.00")
            criterion.max_score = Decimal("5.00")
            criterion.score_type = ScoringCriterion.ScoreType.NUMERIC
            criterion.is_required = True
            criterion.is_active = True
            criterion.order = order
            criterion.full_clean()
            criterion.save()

            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb} criterion: {criterion.name}"))

        retired = 0
        for criterion in ScoringCriterion.objects.filter(is_active=True).exclude(
            name__in=RUBRIC_NAMES
        ):
            criterion.is_active = False
            criterion.save(update_fields=["is_active", "updated_at"])
            retired += 1
            self.stdout.write(
                self.style.WARNING(f"Deactivated legacy criterion: {criterion.name}")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"CEDA/BIA rubric ready: {len(CEDA_RUBRIC)} active criteria, "
                f"{retired} legacy criteria deactivated."
            )
        )
