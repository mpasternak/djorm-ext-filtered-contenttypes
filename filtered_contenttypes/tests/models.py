# -*- encoding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType

from django.db import models
from filtered_contenttypes.fields import FilteredGenericForeignKey


class Phone(models.Model):
    name = models.TextField()

    class Meta:
        app_label = 'tests'


class Monitor(models.Model):
    brand = models.TextField()

    class Meta:
        app_label = 'tests'


class Laptop(models.Model):
    memory = models.IntegerField()

    class Meta:
        app_label = 'tests'


class StorageRecord(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    item = FilteredGenericForeignKey('content_type', 'object_id')

    quantity = models.IntegerField()

    class Meta:
        app_label = 'tests'

class PromoItems(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    item = FilteredGenericForeignKey('content_type', 'object_id')

    class Meta:
        app_label = 'tests'


class Amalgamation_View(models.Model):
    """This view consists of all the Phone, Monitor and Laptop objects.
    You can use it to build global search or generate reports from many
    tables easily. See comments in tests/migrations/003_amalgamation.py
    """

    item = FilteredGenericForeignKey('content_type', 'object_id')
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()

    # This is the fake ID. Yes, this is pretty redundnat, as we have
    # all needed information in content_type_id + object_id columns,
    # but ATM Django does not support compound indexes, so:
    fake_id = models.TextField(primary_key=True)

    # If you want to be able to

    class Meta:
        app_label = 'tests'
        managed = True
