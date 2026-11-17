import datetime

from django.db import migrations, models


def text_field(max_length=255):
    return models.CharField(default="", max_length=max_length)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0004_application_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="business_location",
            field=text_field(),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="application",
            name="business_nature",
            field=text_field(),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="application",
            name="company_no",
            field=text_field(),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="application",
            name="contact_person",
            field=text_field(),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="application",
            name="email",
            field=models.EmailField(default="", max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="application",
            name="incorporation_date",
            field=models.DateField(default=datetime.date(1970, 1, 1)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="application",
            name="loan_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="application",
            name="telephone",
            field=text_field(),
            preserve_default=False,
        ),
    ]
