# -*- encoding: utf-8 -*-
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Lookup

from django.contrib.contenttypes.models import ContentType
from django.db.models.lookups import RegisterLookupMixin
from django.db.models.query import QuerySet
from django.utils.itercompat import is_iterable


from django.db import models


class FilteredGenericForeignKeyFilteringException(Exception):
    pass


class FilteredGenericForeignKey(RegisterLookupMixin, GenericForeignKey):
    """This is a GenericForeignKeyField, that can be used to perform
    filtering in Django ORM.
    """

    def get_prep_lookup(self, lookup_name, rhs):
        """
        Perform preliminary non-db specific lookup checks and conversions
        """
        if lookup_name == 'exact':
            if not isinstance(rhs, models.Model):
                raise FilteredGenericForeignKeyFilteringException(
                    "For exact lookup, please pass a single Model instance.")

        elif lookup_name == 'in':
            if type(rhs) == QuerySet:
                return rhs, None

            if not is_iterable(rhs):
                raise FilteredGenericForeignKeyFilteringException(
                    "For 'in' lookup, please pass an iterable or a QuerySet.")

        else:
            raise FilteredGenericForeignKeyFilteringException(
                "Lookup %s not supported." % lookup_name)

        return rhs, None


    def get_db_prep_lookup(self, lookup_name, param, db, prepared, **kw):

        rhs, _ignore = param

        if lookup_name == 'exact':
            ct_id = ContentType.objects.get_for_model(rhs).pk
            return "(%s, %s)", (ct_id, rhs.pk)

        elif lookup_name == 'in':

            if isinstance(rhs, QuerySet):
                # QuerSet was passed. Don't fetch its items. Use server-side
                # subselect, which will be way faster.

                compiler = rhs.query.get_compiler(connection=db)

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
                    model=rhs.model._meta.model_name,
                    app_label=rhs.model._meta.app_label)

                return query, compiled_args

            if is_iterable(rhs):
                buf = []
                for elem in rhs:
                    if isinstance(elem, models.Model):
                        buf.append((ContentType.objects.get_for_model(elem).pk, elem.pk))
                    elif isinstance(elem, tuple) and type(elem[0]) == int and type(elem[1]) == int and len(elem)==2:
                        buf.append(elem)
                    else:
                        raise FilteredGenericForeignKeyFilteringException(
                            "Unknown type: %r" % type(elem))


                query = ",".join(["%s"] * len(buf))
                return query, buf

            raise NotImplementedError("You passed %r and I don't know what to do with it" % rhs)

        else:
            raise FilteredGenericForeignKeyFilteringException(
                "Unsupported lookup_name: %r" % lookup_name)
    pass


class FilteredGenericForeignKeyLookup(Lookup):
    def as_sql(self, qn, connection):
        ct_attname = self.lhs.output_field.model._meta.get_field(
            self.lhs.output_field.ct_field).get_attname()

        lhs = '("%s".%s, "%s".%s)' % (
            self.lhs.alias,
            self.lhs.output_field.ct_field + "_id",
            self.lhs.alias,
            self.lhs.output_field.fk_field)

        rhs, rhs_params = self.process_rhs(qn, connection)

        # in
        subquery, args = rhs_params
        return "%s %s (%s)" % (lhs, self.operator, subquery), args


class FilteredGenericForeignKeyLookup_Exact(FilteredGenericForeignKeyLookup):
    lookup_name = 'exact'
    operator = '='


class FilteredGenericForeignKeyLookup_In(FilteredGenericForeignKeyLookup):
    lookup_name = 'in'
    operator = 'in'


FilteredGenericForeignKey.register_lookup(
    FilteredGenericForeignKeyLookup_Exact)
FilteredGenericForeignKey.register_lookup(
    FilteredGenericForeignKeyLookup_In)
