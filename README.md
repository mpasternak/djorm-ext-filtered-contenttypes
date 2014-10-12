djorm-ext-filtered-contenttypes
===============================

[![Build Status](https://travis-ci.org/mpasternak/djorm-ext-filtered-contenttypes.svg?branch=master)](https://travis-ci.org/mpasternak/djorm-ext-filtered-contenttypes)
[![Coverage Status](https://img.shields.io/coveralls/mpasternak/djorm-ext-filtered-contenttypes.svg)](https://coveralls.io/r/mpasternak/djorm-ext-filtered-contenttypes)

A GenericForeignKey, that can be filtered &amp; indexed server-side using subqueries.

Supports Python 2.7 and 3.3. Requires Django 1.7. 

Created for and tested with PosgreSQL - feel free to submit patches for other databases.


Introduction
------------

Django supports a mechanism for storing a ForeignKey-like reference to any object, using the django.contrib.contenttypes app.
The key, called GenericForeignKey is internally stored as 2 id fields, content_type_id and object_id.

Current Django documentation says, that it is impossible to filter using GenericForeignKey field. In some use cases this may be a serious limitation of otherwise working ORM. This package fixes that. 

So, when your model looks like this:

```python
    from django.db import models
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.contenttypes.fields import GenericForeignKey
    
    class Foo(models.Model):
        content_type = models.ForeignKey(ContentType)
        object_id = models.PositiveIntegerField()
        item = GenericForeignKey('content_type', 'object_id')
```
All you need to use this package is to replace `GenericForeignKey` with `FilteredGenericForeignKey` like this:
```python
    from django.db import models
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.contenttypes.fields import GenericForeignKey
    from filtered_contenttypes.fields import FilteredGenericForeignKey
    
    class Foo(models.Model):
        content_type = models.ForeignKey(ContentType)
        object_id = models.PositiveIntegerField()
        item = FilteredGenericForeignKey('content_type', 'object_id')
```
and then, you can use it in your application:
```python
    >>> Foo.objects.filter(item__in=SometItem.objects.filter(...))
    [<Foo>, <Foo>, <Foo>]
    >>> Foo.objects.filter(item=OtherItem.objects.get(pk=5))
    [<Foo>]
```

Database benefits
-----------------
As the author of this package (ab)uses PostgreSQL on a daily basis, this package does no different. First, it is imporant, that you create a proper index, using
two fields:
```sql
CREATE UNIQUE INDEX foo_item_idx ON foo(content_type_id, object_id)
```
From the database point of view, the generated query looks like this:
```sql
    SELECT ... FROM ... WHERE (table.content_type_id, table.object_id) IN (...)
```
Yes - we are querying 2 fields at once. And this, in turn, uses that unique index created just a while ago (you created it, didn't you?). 

Perhaps the best thing about this package in terms of scalability is, that when you pass a QuerySet to filtering function or a Q object, the query will be executed server-side. Using it like this:

```python
    Foo.objects.filter(item__in=SomeOther.objects.filter(...))
```

will generate a *single* query. 

Classes
-------

`filtered_contenttypes.fields.FilteredGenericForeignKeyField` - a subclass of GenericForeignKey, that supports filtering.

How to use it
-------------

Just use FilteredGenericForeignKey instead of GenericForeignKey field. There should be no side-effects, as the only new functionality is the filter lookups.

.. code-block:: python

    from filtered_contenttypes.fields import FilteredGenericForeignKey
    from django.db import models

    class Bread(models.Model):
        weight = models.IntegerField(...)

    class Butter(models.Model):
        how_much_fat = models.DecimalField(...)

    class Milk(models.Model):
        bottle_type = models.TextField(...)

    class ShoppingCartEntry(models.Model):
        content_type = models.ForeignKey(ContentType)
        object_id = models.PositiveIntegerField()

        item = FilteredGenericForeignKey('content_type', 'object_id')
        quantity = models.PositiveIntegerField()

Now, somewhere, preferably in your migrations, create a compound index for
the GenericForeignKey:

Now, let's play:

.. code-block:: python

    # After having some items in the cart:

    # return all entries with glass milk bottles
    ShoppingCart.objects.filter(
        item__in=Milk.objects.filter(bottle_type='glass'))

    # return all entries with bread ~0.5kg or milk in glass bottle
    ShoppingCart.objects.filter(
        item=[Bread.objects.get(weight=500),
              Milk.objects.get(bottle_type='glass')])

    # in some cases, it may be useful to query directly for a list of
    # (content_type_id, object_id) entries.
    ShoppingCart.objects.filter(item__in=[(3,2), (3,3), (3,4)])


Changelog
---------

**0.1**

- Initial release
