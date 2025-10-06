from django.apps import apps
from django.db import connection


def get_schema_context():
    """
    Build a simplified schema description for Gemini.
    Lists tables and their columns.
    """
    schema = []

    for model in apps.get_models():
        table = model._meta.db_table
        fields = []
        for field in model._meta.get_fields():
            if hasattr(field, "column") and field.column:
                ftype = field.get_internal_type()
                fields.append(f"{field.column} ({ftype})")
        schema.append(f"Table: {table}\n  Columns: {', '.join(fields)}")

    return "\n\n".join(schema)


def get_live_schema_from_db():
    """
    Uses the actual DB introspection (optional).
    """
    introspection = connection.introspection
    output = []
    with connection.cursor() as cursor:
        for table in introspection.table_names():
            columns = introspection.get_table_description(cursor, table)
            col_names = [col.name for col in columns]
            output.append(f"Table: {table}\n  Columns: {', '.join(col_names)}")
    return "\n\n".join(output)