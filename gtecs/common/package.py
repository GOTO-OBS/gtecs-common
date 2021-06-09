"""Package management functions."""

import os

import configobj

from importlib.metadata import version
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Python < 3.7
    import importlib_resources as pkg_resources  # type: ignore

import validate


def load_config(package, config_file):
    """Load and validate package configuration file.

    Parameters
    ----------
    package : str
        The gtecs subpackage name (e.g. 'control', 'obs', 'alert')

    config_file : str, or list of str
        The name for the package config file (e.g. '`.gtecs.conf')

    """
    # Load package configspec file
    spec = pkg_resources.read_text(f'gtecs.{package}.data', 'configspec.ini').split('\n')

    # Create empty spec for default parameters
    config = configobj.ConfigObj({}, configspec=spec)

    # Try to find the config file, look in the home directory and
    # anywhere specified by GTECS_CONF environment variable
    if isinstance(config_file, str):
        filenames = [config_file]
    else:
        filenames = config_file
    home = os.path.expanduser('~')
    paths = [home, os.path.join(home, 'gtecs'), os.path.join(home, '.gtecs')]
    if 'GTECS_CONF' in os.environ:
        paths.append(os.environ['GTECS_CONF'])
    config_file = None
    config_path = None
    for path in paths:
        for file in filenames:
            try:
                with open(os.path.join(path, file)) as source:
                    config = configobj.ConfigObj(source, configspec=spec)
                    config_file = file
                    config_path = path
                    break
            except IOError:
                pass
    if config_file is not None and config_path is not None:
        loc = os.path.join(config_path, config_file)
    else:
        loc = None

    # Validate ConfigObj, filling defaults from configspec if missing from config file
    validator = validate.Validator()
    result = config.validate(validator)
    if result is not True:
        print('Config file validation failed')
        print([k for k in result if not result[k]])
        raise ValueError(f'{config_file} config file validation failed')

    return config, spec, loc


def get_package_version(package):
    """Load and validate package configuration file.

    Parameters
    ----------
    package : str
        The gtecs subpackage name (e.g. 'control', 'obs', 'alert')

    """
    return version(f'gtecs-{package}')
