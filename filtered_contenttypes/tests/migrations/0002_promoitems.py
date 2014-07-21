# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.db.migrations.operations.special import RunSQL


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '__first__'),
        ('tests', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromoItems',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
