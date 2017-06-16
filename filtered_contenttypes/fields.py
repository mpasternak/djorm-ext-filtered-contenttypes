# -*- encoding: utf-8 -*-
import django

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Lookup, Model

from django.contrib.contenttypes.models import ContentType
from django.db.models.lookups import RegisterLookupMixin
from django.db.models.query import QuerySet
from django.db.models.sql.query import Query
from django.utils.functional import cached_property
from django.utils.itercompat import is_iterable


class FilteredGenericForeignKeyFilteringException(Exception):
    pass


class FilteredGenericForeignKey(RegisterLookupMixin, GenericForeignKey):
    """This is a kind of GenericForeignKeyField, that can be used to perform
    filtering in Django ORM.
    """

    # For django/db/models/sql/query.py is_nullable
    null = False

    # Bypass check introduced in Django 1.8 in django/db/models/sql/query.py line 1372
    related_model = "(this is a hack)"

    class FakeHackModel:
        class _meta:
            concrete_model = None

    model = FakeHackModel
    # End of hack for query.py line 1372

    # Needed to fix https://code.djangoproject.com/ticket/25747 for Django 1.9
    is_relation = False

    def __init__(self, *args, **kw):
        # The line below is needed to bypass this
        # https://github.com/django/django/commit/572885729e028eae2f2b823ef87543b7c66bdb10
        # thanks to MarkusH @ freenode for help
        self.attname = self.related = '(this is a hack)'
        # this is needed when filtering(this__contains=x, this__not_contains=y)
        self.null = False
        GenericForeignKey.__init__(self, *args, **kw)

    def get_prep_lookup(self, lookup_name, rhs):
        """
        Perform preliminary non-db specific lookup checks and conversions
        """
        if lookup_name == 'exact':
            if not isinstance(rhs, Model):
                raise FilteredGenericForeignKeyFilteringException(
                    "For exact lookup, please pass a single Model instance.")

        elif lookup_name in ['in', 'in_raw']:
            if type(rhs) == QuerySet:
                return rhs, None

            if not is_iterable(rhs):
                raise FilteredGenericForeignKeyFilteringException(
                    "For 'in' lookup, please pass an iterable or a QuerySet.")

        else:
            raise FilteredGenericForeignKeyFilteringException(
                "Lookup %s not supported." % lookup_name)

        return rhs, None

    # Copy-paste from Django 1.8 django/db/models/fields/__init__.py class Field
    def get_col(self, alias, output_field=None):
        if output_field is None:
            output_field = self
        if alias != self.model._meta.db_table or output_field != self:
            from django.db.models.expressions import Col
            return Col(alias, self, output_field)
        else:
            return self.cached_col

    @cached_property
    def cached_col(self):
        from django.db.models.expressions import Col
        return Col(self.model._meta.db_table, self)
    # End of copy-paste from class Field


class FilteredGenericForeignKeyLookup(Lookup):

    def get_db_prep_lookup(self, value, connection):
        if not is_iterable(value):
            value = [value]
        ret = []
        for elem in value:
            ret.append((ContentType.objects.get_for_model(elem).pk, elem.pk))

        return (",".join(["%s"]*len(value)),ret)

    def as_sql(self, qn, connection):
        ct_attname = self.lhs.output_field.model._meta.get_field(
            self.lhs.output_field.ct_field).get_attname()

        lhs = '(%s."%s", %s."%s")' % (
            self.lhs.alias,
            self.lhs.output_field.ct_field + "_id",
            self.lhs.alias,
            self.lhs.output_field.fk_field)

        rhs, rhs_params = self.get_db_prep_lookup(self.rhs, connection)

        # in
        # subquery, args = rhs_params
        return "%s %s (%s)" % (lhs, self.operator, rhs), rhs_params


class FilteredGenericForeignKeyLookup_Exact(FilteredGenericForeignKeyLookup):
    def get_db_prep_lookup(self, value, connection):
        if django.VERSION < (1, 10):
            value = value[0]
        ct_id = ContentType.objects.get_for_model(value).pk
        return "(%s, %s)", (ct_id, value.pk)

    lookup_name = 'exact'
    operator = '='


class FilteredGenericForeignKeyLookup_In(FilteredGenericForeignKeyLookup):
    lookup_name = 'in'
    operator = 'in'

    def get_db_prep_lookup(self, value, connection):
        if django.VERSION < (1, 10):
            value = value[0]

        if isinstance(value, QuerySet):
            value = value.query

        if isinstance(value, Query):
            # QuerSet was passed. Don't fetch its items. Use server-side
            # subselect, which will be faster. Get the content_type_id
            # from django_content_type table.

            compiler = value.get_compiler(connection=connection)

            compiled_query, compiled_args = compiler.as_sql()

            query = """
            SELECT
                %(django_content_type_db_table)s.id AS content_type_id,
                U0.id AS object_id
            FROM
                %(django_content_type_db_table)s,
                (%(compiled_query)s) U0
            WHERE
                %(django_content_type_db_table)s.model = '%(model)s' AND
                %(django_content_type_db_table)s.app_label = '%(app_label)s'
            """ % dict(
                django_content_type_db_table=ContentType._meta.db_table,
                compiled_query=compiled_query,
                model=value.model._meta.model_name,
                app_label=value.model._meta.app_label)

            return query, compiled_args

        if is_iterable(value):
            buf = []
            for elem in value:
                if isinstance(elem, Model):
                    buf.append(
                        (ContentType.objects.get_for_model(elem).pk, elem.pk))
                else:
                    raise FilteredGenericForeignKeyFilteringException(
                        "Unknown type: %r" % type(elem))

            query = ",".join(["%s"] * len(buf))
            return query, buf

        raise NotImplementedError(
            "You passed %r and I don't know what to do with it" % value)

class FilteredGenericForeignKeyLookup_In_Raw(FilteredGenericForeignKeyLookup):
    """
    in_raw lookup will not try to get the content_type_id of the right hand
    side QuerySet of the lookup, but instead it will re-write the query, so
    it selects columns named 'content_type_id' and 'object_id' from the right-
    hand side QuerySet. See comments in
    FilteredGenericForeignKeyLookup.get_db_prep
    """
    lookup_name = 'in_raw'
    operator = 'in'


    def get_db_prep_lookup(self, value, connection):
        if django.VERSION < (1, 10):
            value = value[0]

        if isinstance(value, QuerySet):
            value = value.query

        if isinstance(value, Query):
            # Use the passed Query as a 'raw' one - it selects 2 fields
            # first is content_type_id, second is object_id

            compiler = value.get_compiler(connection=connection)
            compiled_query, compiled_args = compiler.as_sql()

            # XXX: HACK AHEAD. Perhaps there is a better way to change
            # select, preferably by using extra. I need to have the proper
            # order of columns AND the proper count of columns, which
            # is no more, than two.
            #
            # Currently, even if I use "only", I have no control over
            # the order of columns. And, if I use
            # .extra(select=SortedDict([...]), I get the proper order
            # of columns and the primary key and other two columns even
            # if I did not specify them in the query.
            #
            # So, for now, let's split the query on first "FROM" and change
            # the beginning part with my own SELECT:

            compiled_query = "SELECT content_type_id, object_id FROM " + \
                             compiled_query.split("FROM", 1)[1]

            return compiled_query, compiled_args

        if is_iterable(value):
            buf = []

            for elem in value:
                if isinstance(elem, tuple) and type(elem[0]) == int and type(
                        elem[1]) == int and len(elem) == 2:
                    buf.append(elem)
                else:
                    raise FilteredGenericForeignKeyFilteringException(
                        "If you pass a list of tuples as an argument, every tuple "
                        "must have exeactly 2 elements and they must be integers")

            query = ",".join(["%s"] * len(buf))
            return query, buf


FilteredGenericForeignKey.register_lookup(FilteredGenericForeignKeyLookup_Exact)
FilteredGenericForeignKey.register_lookup(FilteredGenericForeignKeyLookup_In)
FilteredGenericForeignKey.register_lookup(FilteredGenericForeignKeyLookup_In_Raw)
