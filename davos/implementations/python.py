# ADD DOCSTRING


# TODO: add __all__


import locale
import shlex
import signal
import sys
from subprocess import CalledProcessError, PIPE, Popen


def _activate_helper(smuggle_func, parser_func): ...


def _deactivate_helper(smuggle_func, parser_func): ...


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
