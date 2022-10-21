# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-07-23 14:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('note', '0012_note_is_deleted'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='note',
            options={'ordering': ('-date_modified', 'note'), 'verbose_name_plural': 'Notes'},
        ),
        migrations.RenameField(
            model_name='note',
            old_name='date',
            new_name='date_created',
        ),
        migrations.AddField(
            model_name='note',
            name='date_modified',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date Modified'),
        ),
        migrations.RunSQL(
            ["UPDATE note_note SET date_modified = date_created"],
            "",
        ),
    ]