djorm-ext-filtered-contenttypes
===============================

A GenericForeignKey, that can be filtered &amp; indexed server-side using subqueries.

Requires Django >= 1.7 & PosgreSQL.


Introduction
------------

Django supports a mechanism for storing a ForeignKey-like reference to any object, using the django.contrib.contenttypes app.
The key, called GenericForeignKey is internally stored as 2 id fields, content_type_id and object_id.

Current Django documentation says, that it is impossible to use GenericForeignKey in filter clauses. This package fixes that. The good thing is,
that when using PostgreSQL, you can create a compound index on both fields and use them in queries. That's right, the SQL query looks like this:

.. code-block:: sql

    SELECT ... FROM ... WHERE (table.content_type_id, table.object_id) IN (...)

and if you create a proper index for this table, like:

.. code-block:: sql

      CREATE UNIQUE INDEX shopping_cart_item_idx ON shopping_cart_entry
        USING BTREE(content_type, object_id);

it will be used and your queries will be blazing fast.

Another good thing in terms of scalability is, that when you pass a QuerySet to filtering function or a Q object, the query will be executed server-side, so with this package it is possible to have blazing-fast GenericForeignKey relations.


Classes
^^^^^^^

`filtered_contenttypes.fields.FilteredGenericForeignKeyField`
    A subclass of GenericForeignKey, that supports filtering.

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
