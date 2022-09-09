"""Functions for dealing with system processes."""

import abc
import signal
import socket
import subprocess
import sys
from contextlib import contextmanager

import pid

from . import config


def get_local_ip():
    """Get local IP address.

    https://stackoverflow.com/a/28950776
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip_addr = s.getsockname()[0]
    except Exception:
        ip_addr = '127.0.0.1'
    finally:
        s.close()
    return ip_addr


def execute_command(command_string, timeout=30):
    """Execute a command that should return quickly."""
    print('{}:'.format(command_string))
    try:
        p = subprocess.Popen(command_string,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        ret_str, _ = p.communicate(timeout=timeout)
        print('> ' + ret_str.strip().decode().replace('\n', '\n> '))
        return 0
    except subprocess.TimeoutExpired:
        print('Command {} timed out after {}s'.format(command_string, timeout))
        return 1


def execute_long_command(command_string):
    """Execute a command that might not return immediately.

    For example the tail command for logs (because you can use tail's -f param),
    or obs_scripts.

    """
    print(command_string)
    p = subprocess.Popen(command_string, shell=True, close_fds=True)
    try:
        p.wait()
    except KeyboardInterrupt:
        print('...ctrl+c detected - closing ({})...'.format(command_string))
        try:
            p.terminate()
        except OSError:
            pass
        p.wait()


def kill_process(pid_name, host='127.0.0.1', verbose=False):
    """Kill any specified processes."""
    pid = get_pid(pid_name, host)

    command_string = 'kill -9 {}'.format(pid)
    if host not in ['127.0.0.1', get_local_ip()]:
        command_string = "ssh {} '{}'".format(host, command_string)

    if verbose:
        print(command_string)
    output = subprocess.getoutput(command_string)
    if 'No route to host' in output:
        raise ConnectionError('Cannot connect to host {}'.format(host))

    clear_pid(pid_name, host)

    print('Killed process {} on {}'.format(pid, host))


class MultipleProcessError(Exception):
    """To be used if multiple instances of a process are detected."""

    pass


def get_pid_path():
    """Get the default directory where PID files are stored."""
    return config.CONFIG_PATH / 'pid'


@contextmanager
def make_pid_file(pid_name):
    """Create a PID file."""
    try:
        pid_path = get_pid_path()
        with pid.PidFile(pid_name, pid_path):
            yield
    except pid.PidFileError:
        # there can only be one
        raise MultipleProcessError('Process "{}" already running'.format(pid_name))


def get_pid(pid_name, host='127.0.0.1', verbose=False):
    """Check if a pid file exists with the given name.

    Returns the pid if it is found, or None if not.
    """
    # pid.PidFile(pid_name, pid_path).check() is nicer,
    # but won't work with remote machines
    pid_file = pid_name + '.pid'
    pid_path = get_pid_path() / pid_file

    command_string = 'cat {}'.format(pid_path)
    if host not in ['127.0.0.1', get_local_ip()]:
        # NOTE this assumes the pid path is the same on the remote machine,
        # which should be now we've standardised on the ~/.config directory.
        # Unless they changed XDG_CONFIG_HOME for some reason...
        command_string = "ssh {} '{}'".format(host, command_string)

    if verbose:
        print(command_string)
    output = subprocess.getoutput(command_string)
    if 'No route to host' in output:
        raise ConnectionError('Cannot connect to host {}'.format(host))

    if 'No such file or directory' in output:
        return None
    else:
        return int(output)


def clear_pid(pid_name, host='127.0.0.1', verbose=False):
    """Clear a pid in case we've killed the process."""
    pid_file = pid_name + '.pid'
    pid_path = get_pid_path() / pid_file

    command_string = 'rm {}'.format(pid_path)
    if host not in ['127.0.0.1', get_local_ip()]:
        # NOTE: This assumes the pid path is the same on the remote machine,
        # which should be now we've standardised on the ~/.config directory.
        # Unless they changed XDG_CONFIG_HOME for some reason...
        command_string = "ssh {} '{}'".format(host, command_string)

    if verbose:
        print(command_string)
    output = subprocess.getoutput(command_string)
    if 'No route to host' in output:
        raise ConnectionError('Cannot connect to host {}'.format(host))

    if not output or 'No such file or directory' in output:
        return 0
    else:
        print(output)
        return 1


class NeatCloser(metaclass=abc.ABCMeta):
    """Neatly handles closing down of processes.

    This is an abstract class.

    Implement the tidy_up method to set the commands which
    get run after receiving an instruction to stop
    before the task shuts down.

    Once you have a concrete class based on this abstract class,
    simply create an instance of it and the tidy_up function will
    be caused on SIGINT and SIGTERM signals before closing.
    """

    def __init__(self, task_name):
        self.task_name = task_name
        # redirect SIGTERM, SIGINT to us
        signal.signal(signal.SIGTERM, self.interrupt)
        signal.signal(signal.SIGINT, self.interrupt)

    def interrupt(self, sig, handler):
        """Catch interrupts."""
        print('{} received kill signal'.format(self.task_name))
        # do things here on interrupt
        self.tidy_up()
        sys.exit(1)

    @abc.abstractmethod
    def tidy_up(self):
        """Must be implemented to define tasks to run when closed before process is over."""
        return
