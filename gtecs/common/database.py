"""Database management functions."""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker


def get_engine(user, password, db_name='gtecs', host='localhost',
               encoding='utf8', echo=False, pool_pre_ping=True,
               **kwargs):
    """Create a new database engine.

    Parameters
    ----------
    user : str
        The user name to use when connecting to the database.
    password : str
        The password to use when connecting to the database.

    db_name : str, default='gtecs'
        The name of the database to connect to.
    host : str, default='localhost'
        The host name to use when connecting to the database.
    encoding : str, default='utf8'
        The encoding to use when connecting to the database.
    echo : bool, default=False
        Whether to echo SQL commands to the console.
    pool_pre_ping : bool, default=True
        Whether to ping the database before each connection.

    **kwargs
        Additional keyword arguments to pass to `sqlalchemy.create_engine`.

    Returns
    -------
    engine : sqlalchemy.engine.base.Engine
        The database engine.

    """
    url = '{}:{}@{}'.format(user, password, host)

    if db_name:
        url = os.path.join(url, db_name)
    else:
        # db_name = None is used to connect to the "postgres" database
        url = os.path.join(url, 'postgres')

    connect_args = {}
    connect_args['client_encoding'] = encoding
    connect_args['application_name'] = 'python (gtecs)'

    engine = create_engine(f'postgresql://{url}',
                           echo=echo,
                           pool_pre_ping=pool_pre_ping,
                           connect_args=connect_args,
                           **kwargs,
                           )
    return engine


def get_session(*args, **kwargs):
    """Create a database session.

    All arguments are passed to `get_engine`.
    """
    engine = get_engine(*args, **kwargs)
    new_session = sessionmaker(bind=engine)
    session = new_session()
    return session


def create_database(base, name, user, password, host='localhost',
                    overwrite=False, description=None, sql_code=None, verbose=False,
                    **kwargs):
    """Create the database with empty tables.

    Parameters
    ----------
    base : sqlalchemy.ext.declarative.declarative_base
        The base class containing metadata which defines the database tables.
    name : str
        The name of the database schema to create under the 'gtecs' database.
    user : str
        The user name to use when connecting to the database.
    password : str
        The password to use when connecting to the database.

    host : str, default='localhost'
        The host name to use when connecting to the database.
    overwrite : bool, optional
        If True and the database already exists then drop it before creating the new one.
        If False and the database already exists then an error is raised.
        Default: False
    description : str, optional
        Any comment to add to the schema.
        Default: None
    sql_code : list of str, optional
        Any SQL code to execute after creating the database.
        Default: None
    verbose : bool, default=False
        If True, echo SQL output.

    **kwargs : dict
        Additional keyword arguments to pass to `get_engine`.

    """
    # First connect to the postgres database to create the gtecs database
    engine = get_engine(user, password, host, db_name=None, echo=verbose, **kwargs)
    with engine.connect() as conn:
        # Try creating the new database
        try:
            # postgres does not allow you to create/drop databases inside transactions
            # (https://stackoverflow.com/a/8977109)
            conn.execute(text('commit'))
            conn.execute(text(f'CREATE DATABASE gtecs WITH OWNER {user}'))
        except ProgrammingError as err:
            if 'exists' in str(err):
                # We don't actually mind if the *database* exists, we want to reset the *schema*
                # Plus there might be other schemas in the database that we don't want to drop!
                pass
            else:
                raise

    # Now connect to the actual gtecs database
    engine = get_engine(user, password, host, echo=verbose, **kwargs)
    with engine.connect() as conn:
        # First drop the schema, if overwrite is true
        if overwrite:
            conn.execute(text(f'DROP SCHEMA IF EXISTS {name} CASCADE'))
        # Now try creating the new schema
        try:
            conn.execute(text(f'CREATE SCHEMA {name}'))
            conn.execute(text('commit'))
            if description is not None:
                conn.execute(text(f"COMMENT ON SCHEMA {name} IS '{description}'"))
        except ProgrammingError as err:
            if 'exists' in str(err):
                err_str = f'Schema "gtecs.{name}" already exists (and overwrite=False)'
                raise ValueError(err_str) from err
            else:
                raise

    # Fill the new database/schema with tables defined in the base class
    base.metadata.create_all(engine)

    # Finally execute any functions or triggers in pure SQL
    if sql_code is not None:
        with engine.connect() as conn:
            for code in sql_code:
                conn.execute(text(code))
                conn.commit()
