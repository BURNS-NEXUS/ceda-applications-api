from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("scoring", "0002_applicationscoring_confirmed_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApplicationAdjudicationScore",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("score", models.DecimalField(decimal_places=2, max_digits=6)),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "adjudication",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scores",
                        to="scoring.applicationadjudication",
                    ),
                ),
                (
                    "criterion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="adjudication_scores",
                        to="scoring.scoringcriterion",
                    ),
                ),
            ],
            options={
                "ordering": ["criterion__order", "criterion__name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("adjudication", "criterion"),
                        name="unique_adjudication_score_per_criterion",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("score__gte", 0)),
                        name="adjudicationscore_score_gte_0",
                    ),
                ],
            },
        ),
    ]
