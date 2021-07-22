# ADD DOCSTRING


__all__ = [
    'auto_restart_rerun',
    'generate_parser_func',
    'prompt_restart_rerun_buttons'
]


import locale
import shlex
import signal
import sys
from contextlib import redirect_stdout
from io import StringIO
from subprocess import CalledProcessError, PIPE, Popen


def _activate_helper(smuggle_func, parser_func):
    raise NotImplementedError(
        "davos does not yet support non-interactive Python environments"
    )


def _check_conda_avail_helper():
    """
    Pure Python implementation of helper function for
    `davos.core.core.check_conda`. Checks whether conda executable is
    available for use
    """
    try:
        with redirect_stdout(StringIO()) as conda_list_output:
            # using `conda list` instead of a more straightforward
            # command so stdout is formatted the same as the IPython
            # implementation (which must use `conda list`)
            _run_shell_command_helper('conda list Python')
    except CalledProcessError:
        return None
    return conda_list_output.getvalue()


def _deactivate_helper(smuggle_func, parser_func):
    raise NotImplementedError(
        "davos does not yet support non-interactive Python environments"
    )


def _run_shell_command_helper(command):
    # ADD DOCSTRING
    cmd = shlex.split(command)
    process = Popen(cmd, stdout=PIPE, stderr=PIPE,
                    encoding=locale.getpreferredencoding())
    try:
        while True:
            retcode = process.poll()
            if retcode is None:
                output = process.stdout.readline()
                if output:
                    sys.stdout.write(output)
            elif retcode != 0:
                # processed returned with non-zero exit status
                raise CalledProcessError(returncode=retcode, cmd=cmd)
    except KeyboardInterrupt:
        # forward CTRL + C to process before raising
        process.send_signal(signal.SIGINT)
        raise


def auto_restart_rerun(pkgs):
    raise NotImplementedError(
        "automatic rerunning not available in non-interactive Python (this "
        "function should not be reachable through normal use)."
    )


def generate_parser_func(line_parser):
    raise NotImplementedError(
        "davos does not yet support non-interactive Python environments"
    )


def prompt_restart_rerun_buttons(pkgs):
    raise NotImplementedError(
        "button-based user input prompts are not available in non-interactive "
        "Python (this function should not be reachable through normal use)."
    )
