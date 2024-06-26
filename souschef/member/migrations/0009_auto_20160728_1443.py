# Generated by Django 1.9.7 on 2016-07-28 14:43

import datetime

from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):
    dependencies = [
        ("member", "0008_auto_20160727_2251"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=datetime.datetime(2016, 7, 28, 14, 43, 48, 708683, tzinfo=utc),
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="member",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                default=datetime.datetime(2016, 7, 28, 14, 43, 52, 836645, tzinfo=utc),
            ),
            preserve_default=False,
        ),
    ]
