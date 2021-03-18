__all__ = [
    'register_smuggler_python',
    'run_shell_command_python',
    'smuggle_python'
]

import locale
import shlex
import signal
import sys
from subprocess import CalledProcessError, PIPE, Popen

from davos import davos


def register_smuggler_python():
    raise NotImplementedError("davos does not currently support pure Python interpreters")


def run_shell_command_python(command):
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
    raise NotImplementedError("davos does not currently support pure Python interpreters")


smuggle_python._register_smuggler = register_smuggler_python
