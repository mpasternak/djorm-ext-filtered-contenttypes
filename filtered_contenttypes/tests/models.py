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