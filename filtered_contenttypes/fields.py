# -*- encoding: utf-8 -*-
import django

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Lookup, Model

from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet
from django.db.models.sql.query import Query
from django.utils.functional import cached_property


def is_iterable(x):
    """Return True if ``x`` is iterable.

    Replacement for ``django.utils.itercompat.is_iterable``, which was
    removed in Django 5.0.
    """
    try:
        iter(x)
    except TypeError:
        return False
    return True


class FilteredGenericForeignKeyFilteringException(Exception):
    pass


class FilteredGenericForeignKey(GenericForeignKey):
    """This is a kind of GenericForeignKeyField, that can be used to perform
    filtering in Django ORM.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This field supports server-side filtering through the custom lookups
        # registered below, but it does not participate in Django's relation
        # graph or reverse querying. GenericForeignKey.__init__ force-sets
        # is_relation = True; presenting it as a non-relation instead lets the
        # ORM resolve ``.filter(item=...)`` / ``.filter(item__in=...)`` without
        # tripping the "cannot be used for reverse querying" check, and keeps it
        # out of the reverse-relation graph.
        self.is_relation = False

    def get_prep_lookup(self, lookup_name, rhs):
        """
        Perform preliminary non-db specific lookup checks and conversions
        """
        if lookup_name == 'exact':
            if not isinstance(rhs, Model):
                raise FilteredGenericForeignKeyFilteringException(
                    "For exact lookup, please pass a single Model instance.")

        elif lookup_name in ['in', 'in_raw']:
            if isinstance(rhs, QuerySet):
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
        # Quote the table/alias exactly the way the compiler does for every
        # other column reference in this query. Django 6.1 started quoting
        # generated table aliases in the FROM clause ("V0" instead of V0), and
        # PostgreSQL folds unquoted identifiers to lower case — so hardcoding
        # the bare alias here produced references to a non-existent "v0".
        #
        # SQLCompiler.quote_name() exists since Django 6.1; on 5.2/6.0 the
        # equivalent (and only) helper is quote_name_unless_alias(), which is
        # deprecated in 6.1 and removed in 7.0.
        quote_name = getattr(qn, "quote_name", None) or qn.quote_name_unless_alias
        alias = quote_name(self.lhs.alias)
        lhs = '(%s."%s", %s."%s")' % (
            alias,
            self.lhs.output_field.ct_field + "_id",
            alias,
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
                if (isinstance(elem, tuple) and len(elem) == 2
                        and isinstance(elem[0], int)
                        and isinstance(elem[1], int)):
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
