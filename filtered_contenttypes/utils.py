# -*- encoding: utf-8 -*-

def amalgamate_sql(app, model, extra_fields=None, table_name=None,
                   view_name=None):
    """This function returns a string, containing SQL to create
    a view exposing given model's content_type_id and object_id,
    with some extra_fields optionally.

    This function does *not* escape or quote its arguments.

    >>> print(utils.amalgamate_sql('tests', 'phone', ['foo', 'x as y']))

            CREATE VIEW tests_phone_view AS
            SELECT
                U0.id::text || '_' || test_phone.id::text AS fake_id,
                U0.id AS content_type_id,
                tests_phone.id AS object_id
                , foo, x as y
            FROM
                tests_phone,
                (SELECT
                    id
                 FROM
                    django_content_type
                 WHERE
                    app_label = 'tests' AND
                    model = 'phone'
                ) U0;
    """

    if extra_fields == None:
        extra_fields = []

    extra_fields = ", ".join(extra_fields)
    if extra_fields:
        extra_fields = ", " + extra_fields

    if not table_name:
        table_name = "%s_%s" % (app, model)

    if not view_name:
        view_name = "%s_view" % table_name

    return """
            CREATE VIEW %(view_name)s AS
            SELECT
                U0.id::text || '_' || %(table_name)s.id AS fake_id,
                U0.id AS content_type_id,
                %(table_name)s.id AS object_id
                %(extra_fields)s
            FROM
                %(table_name)s,
                (SELECT
                    id
                 FROM
                    django_content_type
                 WHERE
                    app_label = '%(app)s' AND
                    model = '%(model)s'
                ) U0;
    """ % dict(view_name=view_name,
               app=app,
               model=model,
               table_name=table_name,
               extra_fields=extra_fields)


def union_sql(view_name, *tables):
    """This function generates string containing SQL code, that creates
    a big VIEW, that consists of many SELECTs.

    >>> utils.union_sql('global', 'foo', 'bar', 'baz')
    'CREATE VIEW global SELECT * FROM foo UNION SELECT * FROM bar UNION SELECT * FROM baz'
    """

    if not tables:
        raise Exception("no tables given")

    ret = ""
    pre = "CREATE VIEW %s AS SELECT * FROM " % view_name

    for table in tables:
        ret += pre + table
        pre = " UNION SELECT * FROM "

    return ret