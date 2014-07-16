# -*- encoding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType

from django.test import TestCase
from filtered_contenttypes.tests.models import StorageRecord, Phone, Monitor, \
    Laptop


class TestFilteredContentTypes(TestCase):
    def setUp(self):
        self.p = Phone.objects.create(name='Sony-Ericsson')
        self.m = Monitor.objects.create(brand='Samsung')
        self.l = Laptop.objects.create(memory=2048)

        for no, elem in enumerate([self.p, self.m, self.l]):
            StorageRecord.objects.create(
                item=elem, quantity=no
            )

    def test_in_queryset(self):
        # The subquery after "item__in" should run server-side, so there should
        # be only one query for this test
        with self.assertNumQueries(1):
            qry = StorageRecord.objects.filter(item__in=Phone.objects.filter(name__startswith='Sony'))
            res = list(qry)

        self.assertEquals(len(res), 1)
        self.assertEquals(res[0].item, self.p)

    def test_single_object(self):
        qry = StorageRecord.objects.filter(item=self.l)
        res = list(qry)

        self.assertEquals(len(res), 1)
        self.assertEquals(res[0].item, self.l)

    def test_in_list_of_instances(self):
        qry = StorageRecord.objects.filter(item__in=[self.l, self.p])
        self.assertEquals(qry.count(), 2)

    def test_in_list_of_integer_tuples(self):
        # In some rare cases you might want this:
        qry = StorageRecord.objects.filter(item__in=[
            (ContentType.objects.get_for_model(self.l).pk, self.l.pk),
            (ContentType.objects.get_for_model(self.p).pk, self.p.pk)
            ])
        self.assertEquals(qry.count(), 2)