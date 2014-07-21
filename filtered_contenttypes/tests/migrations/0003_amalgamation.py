# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.db.migrations.operations.special import RunSQL
from filtered_contenttypes.utils import amalgamate_sql, union_sql


class Migration(migrations.Migration):
    """
    In this migration, we create a view that contains all the items in
    our small test application. This way, we can build a global search
    or a global reporting system easily, using just one view.

    To define our items there, we are going to use a compound primary
    key (content_type_id, object_id). The difficult part ATM is, that Django
    does not support compound keys out of the box, so there will be some
    changes in the code to support this.
    """
    dependencies = [
        ('tests', '0002_promoitems'),
    ]

    operations = [
        RunSQL(amalgamate_sql('tests', 'phone')),
        RunSQL(amalgamate_sql('tests', 'monitor')),
        RunSQL(amalgamate_sql('tests', 'laptop')),
        RunSQL(union_sql('tests_amalgamation_view',
                         'tests_phone_view',
                         'tests_monitor_view',
                         'tests_laptop_view'))
    ]
