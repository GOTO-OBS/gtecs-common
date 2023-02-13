"""Database management functions."""

import os

import numpy as np

import pymysql

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker


# Encode Numpy floats
# https://stackoverflow.com/questions/46205532/
pymysql.converters.encoders[np.float64] = pymysql.converters.escape_float
pymysql.converters.conversions = pymysql.converters.encoders.copy()
pymysql.converters.conversions.update(pymysql.converters.decoders)


def get_engine(user, password, host='localhost', db_name='gtecs', dialect='postgres',
               encoding='utf8', echo=False, pool_pre_ping=True,
               **kwargs):
    """Create a new database engine.

    Parameters
    ----------
    user : str
        The user name to use when connecting to the database.
    password : str
        The password to use when connecting to the database.

    host : str, default='localhost'
        The host name to use when connecting to the database.
    db_name : str, default='gtecs'
        The name of the database to connect to.
    dialect : str, default='postgres'
        The SQL dialect to use.
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
        # db_name = None is used when creating databases
        if 'postgres' in dialect:
            url = os.path.join(url, 'postgres')

    if dialect == 'mysql':
        dialect = 'mysql+pymysql'
        encoding_arg = 'charset'
    elif dialect == 'postgres':
        dialect = 'postgresql'
        encoding_arg = 'client_encoding'
    else:
        raise ValueError(f'Unknown SQL dialect: {dialect}')
    url = f'{dialect.lower()}://{url}?{encoding_arg}={encoding}'

    engine = create_engine(url,
                           echo=echo,
                           pool_pre_ping=pool_pre_ping,
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


def create_database(base, name, user, password, overwrite=False, dialect='postgres',
                    schema_name=None, schema_comment=None, sql_code=None, verbose=False,
                    **kwargs):
    """Create the database with empty tables.

    Parameters
    ----------
    base : sqlalchemy.ext.declarative.declarative_base
        The base class containing metadata which defines the database tables.
    name : str
        The name of the database to create.
    user : str
        The user name to use when connecting to the database.
    password : str
        The password to use when connecting to the database.

    overwrite : bool, optional
        If True and the database already exists then drop it before creating the new one.
        If False and the database already exists then an error is raised.
        Default: False
    dialect : str, optional
        SQL dialect to use.
        Must be either 'mysql' or 'postgres'.
        Default: 'postgres'
    schema_name : str, optional
        The name of the schema to create.
        (Only matters if dialect=postgres)
        Default: None
    schema_comment : str, optional
        The comment to add to the schema.
        (Only matters if dialect=postgres and schema_name is not None)
        Default: None
    sql_code : list of str, optional
        Any SQL code to execute after creating the database.
        Default: None
    verbose : bool, default=False
        If True, echo SQL output.

    **kwargs : dict
        Additional keyword arguments to pass to `get_engine`.

    """
    if dialect not in ['mysql', 'postgres']:
        raise ValueError(f'Unknown SQL dialect: {dialect}')

    if dialect == 'mysql':
        engine = get_engine(user, password, db_name=None, dialect=dialect, echo=verbose, **kwargs)
        with engine.connect() as conn:
            # First drop the database, if overwrite is true
            if overwrite:
                conn.execute(f'DROP DATABASE IF EXISTS `{name}`')
            # Now try creating the new database
            try:
                create_command = f'CREATE DATABASE `{name}`'
                # Set default encoding to UTF8 (see https://dba.stackexchange.com/questions/76788)
                create_command += ' CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
                conn.execute(create_command)
            except ProgrammingError as err:
                if 'exists' in str(err):
                    err_str = f'Database "{name}" already exists (and overwrite=False)'
                    raise ValueError(err_str) from err
                else:
                    raise

    elif dialect == 'postgres':
        # First connect to "None" database
        engine = get_engine(user, password, db_name=None, dialect=dialect, echo=verbose, **kwargs)
        with engine.connect() as conn:
            # Try creating the new database
            try:
                # postgres does not allow you to create/drop databases inside transactions
                # (https://stackoverflow.com/a/8977109)
                conn.execute('commit')
                conn.execute(f'CREATE DATABASE {name}')
            except ProgrammingError as err:
                if 'exists' in str(err):
                    # We don't actually mind if the *database* exists, we want to reset the *schema*
                    # Plus there might be other schemas in the database that we don't want to drop!
                    pass
                else:
                    raise

        # Now connect to the actual database
        engine = get_engine(user, password, db_name=name, dialect=dialect, echo=verbose, **kwargs)
        with engine.connect() as conn:
            # First drop the schema, if overwrite is true
            if overwrite:
                conn.execute(f'DROP SCHEMA IF EXISTS {schema_name} CASCADE')
            # Now try creating the new schema
            try:
                conn.execute(f'CREATE SCHEMA {schema_name}')
                conn.execute('commit')
                if schema_comment is not None:
                    conn.execute(f"COMMENT ON SCHEMA {schema_name} IS '{schema_comment}'")
            except ProgrammingError as err:
                if 'exists' in str(err):
                    err_str = f'Schema "{schema_name}" already exists (and overwrite=False)'
                    raise ValueError(err_str) from err
                else:
                    raise

    # Now fill the new database/schema with tables defined in the base class
    engine = get_engine(user, password, db_name=name, dialect=dialect, echo=verbose, **kwargs)
    base.metadata.create_all(engine)

    # Finally execute any functions or triggers in pure SQL
    if sql_code is not None:
        for code in sql_code:
            with engine.connect() as conn:
                conn.execute(text(code))
