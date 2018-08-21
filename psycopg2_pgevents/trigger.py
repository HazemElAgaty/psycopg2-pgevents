"""This module provides functionality for managing triggers."""
__all__ = ['install_trigger', 'install_trigger_function', 'trigger_function_installed', 'trigger_installed',
           'uninstall_trigger', 'uninstall_trigger_function'
           ]


from psycopg2 import ProgrammingError
from psycopg2.extensions import connection

from psycopg2_pgevents.db import execute


INSTALL_TRIGGER_FUNCTION_STATEMENT = """
SET search_path = public, pg_catalog;

CREATE OR REPLACE FUNCTION pgevents()
RETURNS TRIGGER AS $function$
  DECLARE
    row_id integer;
  BEGIN
    IF (TG_OP = 'DELETE') THEN
      row_id = OLD.id;
    ELSE
      row_id = NEW.id;
    END IF;
    PERFORM pg_notify(
     'pgevents',
      json_build_object(
        'event', TG_OP,
        'schema_name', TG_TABLE_SCHEMA,
        'table_name', TG_TABLE_NAME,
        'id', row_id
      )::text
    );
    RETURN NULL;
  END;
$function$
LANGUAGE plpgsql;

SET search_path = "$user", public;
"""

UNINSTALL_TRIGGER_FUNCTION_STATEMENT = """
DROP FUNCTION IF EXISTS public.pgevents() {modifier};
"""

INSTALL_TRIGGER_STATEMENT = """
SET search_path = {schema}, pg_catalog;

DROP TRIGGER IF EXISTS pgevents ON {schema}.{table};

CREATE TRIGGER pgevents
AFTER INSERT OR UPDATE OR DELETE ON {schema}.{table}
FOR EACH ROW
EXECUTE PROCEDURE public.pgevents();

SET search_path = "$user", public;
"""

UNINSTALL_TRIGGER_STATEMENT = """
DROP TRIGGER IF EXISTS pgevents ON {schema}.{table};
"""

SELECT_TRIGGER_STATEMENT = """
SELECT
    *
FROM
    information_schema.triggers
WHERE
    event_object_schema = '{schema}' AND
    event_object_table = '{table}';
"""


def trigger_function_installed(connection: connection):
    """Test whether or not the pgevents trigger function is installed.

    Parameters
    ----------
    connection: psycopg2.extensions.connection
        Active connection to a PostGreSQL database.

    Returns
    -------
    bool
        True if the trigger function is installed, otherwise False.

    """
    installed = False
    try:
        execute(connection, "SELECT pg_get_functiondef('public.pgevents'::regproc);")
        installed = True
    except ProgrammingError as e:
        if e.args:
            error_stdout = e.args[0].splitlines()
            error = error_stdout.pop(0)
            if error.endswith('does not exist'):
                # Trigger function not installed
                pass
            else:
                # Some other exception; re-raise
                raise e
        else:
            # Some other exception; re-raise
            raise e

    return installed


def trigger_installed(connection: connection, table: str, schema: str='public'):
    """Test whether or not a pgevents trigger is installed for a table.

    Parameters
    ----------
    connection: psycopg2.extensions.connection
        Active connection to a PostGreSQL database.
    table: str
        Table whose trigger-existence will be checked.
    schema: str
        Schema to which the table belongs.

    Returns
    -------
    bool
        True if the trigger is installed, otherwise False.

    """
    installed = False

    statement = SELECT_TRIGGER_STATEMENT.format(
        table=table,
        schema=schema
    )

    result = execute(connection, statement)
    if result:
        installed = True

    return installed


def install_trigger_function(connection: connection, overwrite: bool=False) -> None:
    """Install the pgevents trigger function against the database.

    Parameters
    ----------
    connection: psycopg2.extensions.connection
        Active connection to a PostGreSQL database.
    overwrite: bool
        Whether or not to overwrite existing installation of pgevents trigger function, if existing installation is
        found.

    Returns
    -------
    None

    """
    prior_install = False

    if not overwrite:
        prior_install = trigger_function_installed(connection)

    if not prior_install:
        execute(connection, INSTALL_TRIGGER_FUNCTION_STATEMENT)


def uninstall_trigger_function(connection: connection, force: bool=False) -> None:
    """Uninstall the pgevents trigger function from the database.

    Parameters
    ----------
    connection: psycopg2.extensions.connection
        Active connection to a PostGreSQL database.
    force: bool
        If True, force the un-registration even if dependent triggers are still installed. If False, if there are any
        dependent triggers for the trigger function, the un-registration will fail.

    Returns
    -------
    None

    """
    modifier = ''
    if force:
        modifier = 'CASCADE'
    statement = UNINSTALL_TRIGGER_FUNCTION_STATEMENT.format(modifier=modifier)
    execute(connection, statement)


def install_trigger(connection: connection, table: str, schema: str='public', overwrite: bool=False) -> None:
    """Install a pgevents trigger against a table.

    Parameters
    ----------
    connection: psycopg2.extensions.connection
        Active connection to a PostGreSQL database.
    table: str
        Table for which the trigger should be installed.
    schema: str
        Schema to which the table belongs.
    overwrite: bool
        Whether or not to overwrite existing installation of trigger for the given table, if existing installation is
        found.

    Returns
    -------
    None

    """
    prior_install = False

    if not overwrite:
        prior_install = trigger_installed(connection, table, schema)

    if not prior_install:
        statement = INSTALL_TRIGGER_STATEMENT.format(
            schema=schema,
            table=table
        )
        execute(connection, statement)


def uninstall_trigger(connection: connection, table: str, schema: str='public') -> None:
    """Uninstall a pgevents trigger from a table.

    Parameters
    ----------
    connection: psycopg2.extensions.connection
        Active connection to a PostGreSQL database.
    table: str
        Table for which the trigger should be uninstalled.
    schema: str
        Schema to which the table belongs.

    Returns
    -------
    None

    """
    statement = UNINSTALL_TRIGGER_STATEMENT.format(
        schema=schema,
        table=table
    )
    execute(connection, statement)
