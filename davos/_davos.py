"""
TODO: update me
Module for managing session-wide global objects, switches, and
configurable options for both internal and user settings
"""


__all__ = ['capture_stdout', 'Davos']


import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from subprocess import CalledProcessError


# noinspection PyAttributeOutsideInit
class Davos:
    # ADD DOCSTRING
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def initialize(self):
        # ADD DOCSTRING
        self.confirm_install = False
        self.suppress_stdout = False
        self.smuggled = {}
        try:
            # noinspection PyUnresolvedReferences
            self.ipython_shell = get_ipython()
        except NameError:
            # running with vanilla Python interpreter
            import davos.python as internals
            self.smuggler = internals.smuggle_python
            self.activate_parser = internals.activate_parser_python
            self.deactivate_parser = internals.deactivate_parser_python
            self.parser_is_active = internals.check_parser_active_python
            self._shell_cmd_helper = internals.run_shell_command_python
            self.ipython_shell = None
            self.parser_environment = 'PY'
        else:
            import IPython
            if IPython.version_info[0] < 7:
                # running in Colaboratory or an old IPython/Jupyter
                # Notebook version
                import davos.colab as internals
                self.smuggler = internals.smuggle_colab
                self.activate_parser = internals.activate_parser_colab
                self.deactivate_parser = internals.deactivate_parser_colab
                self.parser_is_active = internals.check_parser_active_colab
                self._shell_cmd_helper = internals.run_shell_command_colab
                self.parser_environment = 'IPY_OLD'
                # store InteractiveShell's original showsyntaxerror
                # method so it can be referenced from our overridden
                # version
                self._ipython_showsyntaxerror_orig = self.ipython_shell.showsyntaxerror
            else:
                # running in a new(-ish) IPython/Jupyter Notebook
                # version
                import davos.jupyter as internals
                self.smuggler = internals.smuggle_jupyter
                self.activate_parser = internals.activate_parser_jupyter
                self.deactivate_parser = internals.deactivate_parser_jupyter
                self.parser_is_active = internals.check_parser_active_jupyter
                self._shell_cmd_helper = internals.run_shell_command_jupyter
                self.parser_environment = 'IPY_NEW'
                # store InteractiveShell's original showsyntaxerror
                # method so it can be referenced from our overridden
                # version
                self._ipython_showsyntaxerror_orig = self.ipython_shell.showsyntaxerror
        self.get_stdlib_modules()
        self.activate_parser()

    def get_stdlib_modules(self):
        # ADD DOCSTRING
        stdlib_dir = Path(io.__file__).parent
        stdlib_modules = set(p.stem for p in stdlib_dir.iterdir())
        try:
            stdlib_modules.remove('site-packages')
        except KeyError:
            pass
        if sys.platform.startswith('linux'):
            try:
                stdlib_modules.remove('dist-packages')
            except KeyError:
                pass
        self.stdlib_modules = stdlib_modules


    def run_shell_command(self, command, live_stdout=None):
        # ADD DOCSTRING
        if live_stdout is None:
            live_stdout = not self.suppress_stdout
        if live_stdout:
            command_context = capture_stdout
        else:
            command_context = redirect_stdout
        with command_context(io.StringIO()) as stdout:
            try:
                return_code = self._shell_cmd_helper(command)
            except CalledProcessError as e:
                # if the exception doesn't record the output, add it
                # manually before raising
                stdout = stdout.getvalue()
                if e.output is None and stdout != '':
                    e.output = stdout
                raise e
            else:
                stdout = stdout.getvalue()
        return stdout, return_code


class capture_stdout:
    # TODO: move me to davos.core?
    """
    Context manager similar to `contextlib.redirect_stdout`, but
    different in that it:
      - temporarily writes stdout to other streams *in addition to*
        rather than *instead of* `sys.stdout`
      - accepts any number of streams and sends stdout to each
      - can optionally keep streams open after exiting context by
        passing `closing=False`

    Parameters
    ----------
    *streams : `*io.IOBase`
        stream(s) to receive data sent to `sys.stdout`

    closing : `bool`, optional
        if [default: `True`], close streams upon exiting the context
        block.
    """
    def __init__(self, *streams, closing=True):
        self.streams = streams
        self.closing = closing
        self.sys_stdout_write = sys.stdout.write

    def __enter__(self):
        sys.stdout.write = self._write
        if len(self.streams) == 1:
            return self.streams[0]
        return self.streams

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout.write = self.sys_stdout_write
        if self.closing:
            for s in self.streams:
                s.close()

    def _write(self, data):
        for s in self.streams:
            s.write(data)
        self.sys_stdout_write(data)
        sys.stdout.flush()
