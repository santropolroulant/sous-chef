# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-07-21 11:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meal', '0003_fix224a'),
    ]

    operations = [
        migrations.AddField(
            model_name='component_ingredient',
            name='date',
            field=models.DateField(blank=True, null=True, verbose_name='date'),
        ),
    ]