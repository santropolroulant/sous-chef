# Generated by Django 1.9.5 on 2016-06-05 19:24

import datetime

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("meal", "0001_fix161f"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Address",
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
                    "number",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="street number"
                    ),
                ),
                ("street", models.CharField(max_length=100, verbose_name="street")),
                (
                    "apartment",
                    models.CharField(
                        blank=True, max_length=10, null=True, verbose_name="apartment"
                    ),
                ),
                (
                    "floor",
                    models.IntegerField(blank=True, null=True, verbose_name="floor"),
                ),
                ("city", models.CharField(max_length=50, verbose_name="city")),
                (
                    "postal_code",
                    models.CharField(max_length=6, verbose_name="postal code"),
                ),
            ],
            options={
                "verbose_name_plural": "addresses",
            },
        ),
        migrations.CreateModel(
            name="Client",
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
                    "billing_payment_type",
                    models.CharField(
                        choices=[
                            ("", "Payment type"),
                            ("check", "Check"),
                            ("cash", "Cash"),
                            ("debit", "Debit card"),
                            ("credit", "Credit card"),
                            ("eft", "EFT"),
                        ],
                        max_length=10,
                        null=True,
                        verbose_name="Payment Type",
                    ),
                ),
                (
                    "rate_type",
                    models.CharField(
                        choices=[
                            ("default", "Default"),
                            ("low income", "Low income"),
                            ("solidary", "Solidary"),
                        ],
                        default="default",
                        max_length=10,
                        verbose_name="rate type",
                    ),
                ),
                (
                    "emergency_contact_relationship",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="emergency contact relationship",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("D", "Pending"),
                            ("A", "Active"),
                            ("S", "Paused"),
                            ("N", "Stop: no contact"),
                            ("C", "Stop: contact"),
                            ("I", "Deceased"),
                        ],
                        default="D",
                        max_length=1,
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[("en", "English"), ("fr", "French")],
                        default="fr",
                        max_length=2,
                    ),
                ),
                (
                    "alert",
                    models.TextField(
                        blank=True, null=True, verbose_name="alert client"
                    ),
                ),
                (
                    "delivery_type",
                    models.CharField(
                        choices=[("O", "Ongoing"), ("E", "Episodic")],
                        default="O",
                        max_length=1,
                    ),
                ),
                (
                    "gender",
                    models.CharField(
                        blank="True",
                        choices=[("", "Gender"), ("F", "Female"), ("M", "Male")],
                        default="U",
                        max_length=1,
                        null="True",
                    ),
                ),
                (
                    "birthdate",
                    models.DateField(
                        blank="True", default=django.utils.timezone.now, null="True"
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "clients",
            },
        ),
        migrations.CreateModel(
            name="Client_option",
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
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="member.Client",
                        verbose_name="client",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Contact",
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
                    "type",
                    models.CharField(
                        choices=[
                            ("Home phone", "Home phone"),
                            ("Cell phone", "Cell phone"),
                            ("Work phone", "Work phone"),
                            ("Email", "Email"),
                        ],
                        max_length=100,
                        verbose_name="contact type",
                    ),
                ),
                ("value", models.CharField(max_length=50, verbose_name="value")),
            ],
            options={
                "verbose_name_plural": "contacts",
            },
        ),
        migrations.CreateModel(
            name="Member",
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
                    "firstname",
                    models.CharField(max_length=50, verbose_name="firstname"),
                ),
                ("lastname", models.CharField(max_length=50, verbose_name="lastname")),
                (
                    "address",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="member.Address",
                        verbose_name="address",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "members",
            },
        ),
        migrations.CreateModel(
            name="Note",
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
                ("note", models.TextField(verbose_name="Note")),
                (
                    "date",
                    models.DateField(
                        default=django.utils.timezone.now, verbose_name="Date"
                    ),
                ),
                ("is_read", models.BooleanField(default=False, verbose_name="Is read")),
                (
                    "priority",
                    models.CharField(
                        choices=[("normal", "Normal"), ("urgent", "Urgent")],
                        default="normal",
                        max_length=15,
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="Notes",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Author",
                    ),
                ),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="Notes",
                        to="member.Member",
                        verbose_name="Member",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Notes",
            },
        ),
        migrations.CreateModel(
            name="Option",
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
                ("name", models.CharField(max_length=50, verbose_name="name")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="description"),
                ),
                (
                    "option_group",
                    models.CharField(
                        choices=[
                            ("side dish", "side dish"),
                            ("preparation", "Preparation"),
                            ("week delivery schedule", "Week delivery schedule"),
                        ],
                        max_length=100,
                        verbose_name="option group",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "options",
            },
        ),
        migrations.CreateModel(
            name="Referencing",
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
                ("referral_reason", models.TextField(verbose_name="Referral reason")),
                (
                    "work_information",
                    models.TextField(
                        blank=True, null=True, verbose_name="Work information"
                    ),
                ),
                (
                    "date",
                    models.DateField(
                        default=datetime.date.today, verbose_name="Referral date"
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_referent",
                        to="member.Client",
                        verbose_name="client",
                    ),
                ),
                (
                    "referent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="member.Member",
                        verbose_name="referent",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "referents",
            },
        ),
        migrations.CreateModel(
            name="Restriction",
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
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="member.Client",
                        verbose_name="client",
                    ),
                ),
                (
                    "restricted_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="meal.Restricted_item",
                        verbose_name="restricted item",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="contact",
            name="member",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="member_contact",
                to="member.Member",
                verbose_name="member",
            ),
        ),
        migrations.AddField(
            model_name="client_option",
            name="option",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="member.Option",
                verbose_name="option",
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="billing_member",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="member.Member",
                verbose_name="billing member",
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="emergency_contact",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="emergency_contact",
                to="member.Member",
                verbose_name="emergency contact",
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="member",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="member.Member",
                verbose_name="member",
            ),
        ),
    ]
