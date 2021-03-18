"""
TODO: update me
Module for managing session-wide global objects, switches, and
configurable options for both internal and user settings
"""


__all__ = ['Davos']


import sys
from contextlib import redirect_stdout
from io import StringIO


# noinspection PyAttributeOutsideInit
class Davos:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def initialize(self):
        self.confirm_install = False
        self.suppress_stdout = False
        self.smuggled = set()
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
                self._shell_cmd_helper = internals.run_shell_cmd_colab
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
        with command_context(StringIO()) as stdout:
            return_code = self._shell_cmd_helper(command)
        return stdout.getvalue(), return_code


class capture_stdout:
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