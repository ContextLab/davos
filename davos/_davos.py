"""
TODO: update me
Module for managing session-wide global objects, switches, and
configurable options for both internal and user settings
"""


__all__ = ['Davos']


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
                self._shell_cmd_helper = internals.run_shell_command_colab
                self.parser_environment = 'IPY_OLD'
            else:
                # running in a new(-ish) IPython/Jupyter Notebook
                # version
                import davos.jupyter as internals
                self.smuggler = internals.smuggle_jupyter
                self._shell_cmd_helper = internals.run_shell_command_jupyter
                self.parser_environment = 'IPY_NEW'
        self.smuggler._register()

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
        except CalledProcessError as e:
            # if the exception doesn't record the output, add it
            # manually before raising
            if e.output is None:
                stdout = stdout.getvalue()
                if stdout != '':
                    e.output = stdout
            raise e
        else:
            return stdout.getvalue(), return_code


class capture_stdout:
    # TODO: move me to davos.core?
    """
    Context manager similar to `contextlib.redirect_stdout`, but
    temporarily writes stdout to another stream *in addition to* --
    rather than *instead of* -- `sys.stdout`
    """
    def __init__(self, stream):
        self.stream = stream
        self.sys_stdout_write = sys.stdout.write

    def __enter__(self):
        sys.stdout.write = self._write
        return self.stream

    def __exit__(self, *args):
        sys.stdout.write = self.sys_stdout_write
        self.stream = self.stream.getvalue()

    def _write(self, data):
        self.stream.write(data)
        self.sys_stdout_write(data)
        sys.stdout.flush()


# class nullcontext:
#     """
#     dummy context manager equivalent to contextlib.nullcontext
#     (which isn't implemented for Python<3.7)
#     """
#     def __init__(self, enter_result=None):
#         self.enter_result = enter_result
#
#     def __enter__(self):
#         return self.enter_result
#
#     def __exit__(self, exc_type, exc_value, traceback):
#         return None