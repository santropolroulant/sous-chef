# Generated by Django 1.10 on 2016-09-12 19:23

import annoying.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("order", "0008_auto_20160912_1509"),
    ]

    operations = [
        migrations.CreateModel(
            name="Billing",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "total_amount",
                    models.DecimalField(
                        decimal_places=2, max_digits=6, verbose_name="total_amount"
                    ),
                ),
                ("billing_month", models.IntegerField()),
                ("billing_year", models.IntegerField()),
                ("created", models.DateTimeField(auto_now=True)),
                ("detail", annoying.fields.JSONField()),
                ("orders", models.ManyToManyField(to="order.Order")),
            ],
        ),
    ]
