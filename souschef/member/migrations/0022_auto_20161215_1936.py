# Generated by Django 1.10 on 2016-12-15 19:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("member", "0021_auto_20161125_2055"),
    ]

    operations = [
        migrations.AlterField(
            model_name="client",
            name="billing_payment_type",
            field=models.CharField(
                choices=[
                    (" ", "----"),
                    ("3rd", "3rd Party"),
                    ("credit", "Credit card"),
                    ("eft", "EFT"),
                ],
                max_length=10,
                null=True,
                verbose_name="Payment Type",
            ),
        ),
    ]
