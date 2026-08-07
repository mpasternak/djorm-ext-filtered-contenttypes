djorm-ext-filtered-contenttypes
===============================

[![Tests](https://github.com/mpasternak/djorm-ext-filtered-contenttypes/actions/workflows/tests.yml/badge.svg)](https://github.com/mpasternak/djorm-ext-filtered-contenttypes/actions/workflows/tests.yml)
[![PyPI Version](https://img.shields.io/pypi/v/djorm-ext-filtered-contenttypes)](https://pypi.org/project/djorm-ext-filtered-contenttypes/)
[![Python Version](https://img.shields.io/pypi/pyversions/djorm-ext-filtered-contenttypes)](https://pypi.org/project/djorm-ext-filtered-contenttypes/)
![Django](https://img.shields.io/badge/django-5.2%20%7C%206.0%20%7C%206.1-blue)
[![License](https://img.shields.io/github/license/mpasternak/djorm-ext-filtered-contenttypes)](LICENSE)

A GenericForeignKey, that can be filtered & indexed server-side using subqueries.

Supports Django 5.2 LTS, 6.0 and 6.1 on Python 3.10–3.14. (Previously: Django 1.7–1.11 on Python 2.7/3.5/3.6.)

Created for and tested with PostgreSQL - feel free to submit patches for other databases.


Features
--------

- Filter a `GenericForeignKey` server-side: `.filter(item=obj)`, `.filter(item__in=queryset)`, `.filter(item__in=[obj1, obj2])`.
- Passing a `QuerySet` builds a **single** SQL query using a server-side subselect — no N+1, no pulling primary keys into Python.
- Compound `(content_type_id, object_id) IN (...)` lookups that can use a compound index for fast filtering.
- An `in_raw` lookup for advanced cases: pass a list of `(content_type_id, object_id)` integer tuples, or a QuerySet that already selects those two columns.
- Works inside `Q()` objects: `.filter(Q(item=a) | Q(item=b))`.


Installation
------------

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv add djorm-ext-filtered-contenttypes
```

Using pip:

```bash
pip install djorm-ext-filtered-contenttypes
```

Requires Python 3.10+ and Django 5.2, 6.0 or 6.1. PostgreSQL is required — the filtering relies on PostgreSQL-specific compound-column subqueries.


Supported versions
------------------

Every combination below is exercised in CI:

| Django  | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 |
|---------|:----:|:----:|:----:|:----:|:----:|
| 5.2 LTS |  ✓   |  ✓   |  ✓   |  ✓   |  ✓   |
| 6.0     |  —   |  —   |  ✓   |  ✓   |  ✓   |
| 6.1     |  —   |  —   |  ✓   |  ✓   |  ✓   |


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

```python

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
```

Now, somewhere, preferably in your migrations, create a compound index for
the GenericForeignKey:

Now, let's play:

```python

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
```


Changelog
---------

**Unreleased**

- Added support for Django 6.1 (Python 3.12+), tested in CI alongside 5.2 LTS and 6.0.
- Fixed lookup SQL generation for Django 6.1, which now quotes generated table aliases
  (`"V0"` instead of `V0`). The compound `(content_type_id, object_id)` left-hand side is
  now quoted through the compiler instead of being interpolated bare, which previously made
  PostgreSQL fail with `missing FROM-clause entry for table "v0"` when a filtered queryset
  was used as the right-hand side of `item__in_raw`.

**0.5.1**

- Support Django 5.2 LTS and 6.0 on Python 3.10–3.14 (ported off the old Django 1.x internals).
- Modern packaging: uv + `pyproject.toml`, pytest, GitHub Actions CI, pre-commit (ruff).
- Drop support for Django 1.7–1.11 and Python 2.7/3.5/3.6. Resolves the legacy Django 1.x
  security advisories that applied to the old dependency constraint.

**0.3**

- Support 2.7, 3.5 with Django 1.7, 1.8 and 1.9

**0.1**

- Initial release


License
-------

MIT — see [LICENSE](LICENSE) for details.
