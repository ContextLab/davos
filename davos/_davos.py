"""
TODO: update me
Module for managing session-wide global objects, switches, and
configurable options for both internal and user settings
"""


__all__ = ['Davos', 'capture_stdout']


import sys
from contextlib import redirect_stdout
from io import StringIO
from subprocess import CalledProcessError


# noinspection PyAttributeOutsideInit
class Davos:
    # ADD DOCSTRING
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def confirm_installed_versions(self):
        # run after smuggling all desired packages to confirm all
        # *final* installed versions match requested versions
        ...

    def initialize(self):
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
                self._shell_cmd_helper = internals.run_shell_command_colab
                self.parser_environment = 'IPY_OLD'
            else:
                # running in a new(-ish) IPython/Jupyter Notebook
                # version
                import davos.jupyter as internals
                self.smuggler = internals.smuggle_jupyter
                self.activate_parser = internals.activate_parser_jupyter
                self.deactivate_parser = internals.deactivate_parser_jupyter
                self._shell_cmd_helper = internals.run_shell_command_jupyter
                self.parser_environment = 'IPY_NEW'
        self.activate_parser()

    def run_shell_command(self, command, live_stdout=None):
        if live_stdout is None:
            live_stdout = not self.suppress_stdout
        if live_stdout:
            command_context = capture_stdout
        else:
            command_context = redirect_stdout
        try:
            with command_context(StringIO()) as stdout:
                return_code = self._shell_cmd_helper(command)
                stdout = stdout.getvalue()
        except CalledProcessError as e:
            # if the exception doesn't record the output, add it
            # manually before raising
            if e.output is None and stdout != '':
                e.output = stdout
            raise e
        else:
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
        try:
            sys_ = globals()['sys']
        except KeyError:
            import sys as sys_
        self.sys_ = sys
        self.sys_stdout_write = sys.stdout.write

    def __enter__(self):
        self.sys_.stdout.write = self._write
        if len(self.streams) == 1:
            return self.streams[0]
        return self.streams

    def __exit__(self, exc_type, exc_value, traceback):
        self.sys_.stdout.write = self.sys_stdout_write
        if self.closing:
            for s in self.streams:
                s.close()

    def _write(self, data):
        for s in self.streams:
            s.write(data)
        self.sys_stdout_write(data)
        self.sys_.stdout.flush()
