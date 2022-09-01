"""Package configuration functions."""

import os
from pathlib import Path


def get_config_path():
    """Get the location of the system config directory."""
    # This is based on https://github.com/srstevenson/xdg
    path = os.environ.get('XDG_CONFIG_HOME')
    if path and os.path.isabs(path):
        return Path(path)
    return Path.home() / '.config'


def get_package_config_path(package_name='gtecs'):
    """Get the location of the config directory for the given package."""
    base_path = get_config_path()
    return base_path / package_name


CONFIG_PATH = get_package_config_path()
