# ADD DOCSTRING


__all__ = [
    'activate_parser_python',
    'deactivate_parser_python',
    'run_shell_command_python',
    'smuggle_python',
    'smuggle_parser_python'
]


import locale
import shlex
import signal
import sys
from subprocess import CalledProcessError, PIPE, Popen


def activate_parser_python():
    raise NotImplementedError(
        "davos does not currently support pure Python interpreters"
    )


def deactivate_parser_python():
    raise NotImplementedError(
        "davos does not currently support pure Python interpreters"
    )


def run_shell_command_python(command):
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
            else:
                return retcode
    except KeyboardInterrupt:
        # forward CTRL + C to process before raising
        process.send_signal(signal.SIGINT)
        raise


def smuggle_python():
    raise NotImplementedError(
        "davos does not currently support pure Python interpreters"
    )


def smuggle_parser_python(script_text):
    raise NotImplementedError(
        "davos does not currently support pure Python interpreters"
    )
