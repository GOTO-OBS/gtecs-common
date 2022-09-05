"""Standard format for creating log files."""

import logging
import sys
import time
from io import TextIOBase
from logging import handlers
from pathlib import Path

from . import config


def get_file_handler(name, out_path=None):
    """Get the file handler."""
    if out_path is None:
        out_path = Path.cwd()
    log_file = f'{name}.log'
    log_path = out_path / log_file

    # formatter for stdout logging; does not include name of log
    formatter = logging.Formatter(
        '%(asctime)s:%(levelname)s - %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S'
    )
    formatter.converter = time.gmtime

    handler = handlers.WatchedFileHandler(log_path, delay=True)
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    return handler


def get_stream_handler():
    """Get the stream handler."""
    # formatter for stdout logging; includes name of log
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d:%(name)s:%(levelname)s - %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S'
    )
    formatter.converter = time.gmtime

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    return handler


class StreamToLogger(TextIOBase):
    """Fake file-like stream object that redirects writes to a logger instance."""

    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        """Write to the stream."""
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        """Flush the stream."""
        pass


def get_log_path():
    """Get the default directory where log files are stored."""
    return config.CONFIG_PATH / 'logs'


def get_logger(name, out_path=None, capture_stdout=True, suppress_stdout=False):
    """Provide standardised logging to all processes.

    Each logger will write to stdout and a file name '<name>.log'
    in the directory given by `out_path`.

    By default all levels from DEBUG up are written to the logfile,
    and all levels from INFO up are written to stdout.

    This function will not rename logfiles based on the date. The idea is
    to use the UNIX utility logrotate to rotate the log files daily.

    Parameters
    ----------
    name : str
        the name of the logger, which is also used for the name of the logfile

    out_path : str or None
        path to save log entries to
        if None, default to the module config directory (`config.CONFIG_PATH`/logs/)
    capture_stdout : bool, default=True
        if True, log all stdout not just log commands
    suppress_stdout : bool, default=False
        if True, do not repeat log commands to stdout

    """
    log = logging.getLogger(name)

    # If the handlers are not empty this has been called before,
    # and we shouldn't add more handlers
    if log.handlers != []:
        return log

    # Set the overall log level (also set by the handlers)
    log.setLevel(logging.DEBUG)

    # Add a handler to log to the specified file (<name>.log)
    if out_path is None:
        out_path = get_log_path()
    if not isinstance(out_path, Path):
        out_path = Path(out_path)
    if not out_path.exists():
        out_path.mkdir(parents=True, exist_ok=True)
    log.addHandler(get_file_handler(name, out_path))

    # Add a handler to log to stdout
    if not suppress_stdout:
        log.addHandler(get_stream_handler())

    # Redirect system stdout to the log
    if capture_stdout:
        sys.stdout = StreamToLogger(log, logging.INFO)
        sys.stderr = StreamToLogger(log, logging.ERROR)

    return log
