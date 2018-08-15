from sqlalchemy_pgevents.base import execute

REGISTER_TRIGGER_FUNCTION = """
SET search_path = public, pg_catalog;

CREATE OR REPLACE FUNCTION pgevents()
RETURNS TRIGGER AS $function$
  BEGIN
    PERFORM pg_notify(
       'pgevents',
        json_build_object(
          'schema_name', TG_TABLE_SCHEMA,
          'table_name', TG_TABLE_NAME,
          'id', NEW.id
      )::text
    );
    RETURN NEW;
  END;
$function$
LANGUAGE plpgsql;

SET search_path = "$user", public;
"""

UNREGISTER_TRIGGER_FUNCTION = """
DROP FUNCTION IF EXISTS public.pgevents() CASCADE;
"""

REGISTER_TRIGGER_TEMPLATE = """
SET search_path = {schema}, pg_catalog;

DROP TRIGGER IF EXISTS pgevents ON {schema}.{table};

CREATE TRIGGER pgevents
AFTER INSERT ON {schema}.{table}
FOR EACH ROW
EXECUTE PROCEDURE public.pgevents();

SET search_path = "$user", public;
"""

UNREGISTER_TRIGGER_TEMPLATE = """
DROP TRIGGER IF EXISTS pgevents ON {schema}.{table};
"""


def register_trigger_function(connection):
    execute(connection, REGISTER_TRIGGER_FUNCTION)


def unregister_trigger_function(connection):
    execute(connection, UNREGISTER_TRIGGER_FUNCTION)


def register_trigger(connection, table, schema='public'):
    statement = REGISTER_TRIGGER_TEMPLATE.format(
        schema=schema,
        table=table
    )
    execute(connection, statement)


def unregister_trigger(connection, table, schema='public'):
    statement = UNREGISTER_TRIGGER_TEMPLATE.format(
        schema=schema,
        table=table
    )
    execute(connection, statement)