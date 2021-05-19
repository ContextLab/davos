# ADD DOCSTRING


# TODO: add __all__


import locale
import shlex
import signal
import sys
from contextlib import redirect_stdout
from io import StringIO
from subprocess import CalledProcessError, PIPE, Popen


def _activate_helper(smuggle_func, parser_func): 
    # TODO: implement me
    ...


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
    # TODO: implement me
    ...


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
