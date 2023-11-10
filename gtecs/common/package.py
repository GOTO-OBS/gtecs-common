"""Package management functions."""

import importlib.resources as pkg_resources
import os
from importlib.metadata import version

from configobj import ConfigObj

from fabric.connection import Connection

import validate


def load_config(package, config_file, remote_host=None, remote_user=None):
    """Load and validate package configuration file.

    Parameters
    ----------
    package : str
        The gtecs subpackage name (e.g. 'control', 'obs', 'alert')
    config_file : str, or list of str
        The name for the package config file (e.g. '.gtecs.conf')

    remote_host : str or None, default=None
        If given, load the config file from the given remote host
        This uses fabric to connect through SSH, and assumes that no password is needed.
        Note the remote config file will still be validated based on the local configspec
        for the given gtecs package.
    remote_user : str or None, default=None
        The username to use when connecting to `remote_host`.
        If None then the same username as the client is assumed.

    """
    if isinstance(config_file, str):
        filenames = [config_file]
    else:
        filenames = config_file

    # Options for the location of the config file:
    # - Home directory (~)
    # - ~/gtecs or ~/.gtecs
    # - Any other path given by the 'GTECS_CONF' environment variable
    if remote_host is None:
        home = os.path.expanduser('~')
        paths = [home, os.path.join(home, 'gtecs'), os.path.join(home, '.gtecs')]
        if 'GTECS_CONF' in os.environ:
            paths.append(os.environ['GTECS_CONF'])
    else:
        # The SFTP connection will automatically start in the home directory
        paths = ['', 'gtecs', '.gtecs']
        # We will need to check the remote environment
        # TODO: I'm not sure this works? Depends how the variable is set.
        with Connection(remote_host, user=remote_user) as c:
            result = c.run('echo $GTECS_CONF', hide='both').stdout.strip()
            if result != '':
                paths.append(result)

    # Load package configspec file
    with pkg_resources.open_text(f'gtecs.{package}.data', 'configspec.ini') as spec_file:
        spec = ConfigObj(spec_file, _inspec=True)

    # Search all possible paths for the config file
    config = None
    config_filepath = None
    for path in paths:
        for file in filenames:
            filepath = os.path.join(path, file)
            if remote_host is None:
                try:
                    with open(filepath) as source:
                        config = ConfigObj(source, configspec=spec)
                        config_filepath = filepath
                        break
                except IOError:
                    pass
            else:
                try:
                    with Connection(remote_host, user=remote_user) as c, c.sftp() as sftp:
                        with sftp.open(filepath) as source:
                            config = ConfigObj(source, configspec=spec)
                            config_filepath = filepath
                            break
                except FileNotFoundError:
                    pass

    # We didn't find a file, so just create an empty config to get default parameters
    if config is None:
        config = ConfigObj({}, configspec=spec)

    # Validate ConfigObj, filling defaults from configspec if missing from config file
    validator = validate.Validator()
    result = config.validate(validator)
    if result is not True:
        print('Config file validation failed')
        print([k for k in result if not result[k]])
        raise ValueError(f'{config_file} config file validation failed')

    # Also report any keys in the config that are not in the spec
    # This is useful for catching typos or any deprecated parameters
    for key in config.keys():
        if key not in spec:
            print(f'Warning: {key} in {config_filepath.split("/")[-1]} is not in the configspec')

    return config, spec, config_filepath


def get_package_version(package):
    """Load and validate package configuration file.

    Parameters
    ----------
    package : str
        The gtecs subpackage name (e.g. 'control', 'obs', 'alert')

    """
    return version(f'gtecs-{package}')
