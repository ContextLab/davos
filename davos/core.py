# will hold functions used by all 3 approaches, helper functions, etc.
# once other 2 smugglers are written


import sys
from io import StringIO

from davos import config
from davos.exceptions import InstallerError, OnionValueError

if config.IPYTHON_SHELL is not None:
    from IPython.core.interactiveshell import system as _run_shell_cmd


class Onion:
    # ADD DOCSTRING
    @staticmethod
    def parse_onion_syntax(comment_text):
        # TODO: parse comment string for install arguments, use
        #  https://github.com/ContextLab/CDL-docker-stacks/blob/master/CI/conda_environment.py#L56-L65
        #  for splitting version string
        # NOTE: returns a dict of {param: value} for each, CLI args that
        #  don't take a value should be ... so they don't
        #  conflict with None values in constructor
        ...


    def __init__(self, import_name, installer='pip', install_name=None,
                 version_spec=None, **installer_kwargs):
        # ADD DOCSTRING
        # NOTE: if install_name is None, all kwargs except installer must be None.
        #  Elif install_name is not None, install_name must not be None,
        #  but version et al. still can be
        if install_name is None:
            self.install_name = import_name
        else:
            self.install_name = install_name
        if installer == 'pip' or installer == 'pypi':
            self.install_package = self._pip_install_package
        elif installer == 'conda':
            self.install_package = self._conda_install_package
        else:
            raise InstallerError(
                f"Unsupported installer: '{installer}'. Currently supported "
                "installers are 'pip' and 'conda'"
            )
        self.installer = installer
        self.version_spec = version_spec
        self.installer_kwargs = installer_kwargs

    def _pip_install_package(self):
        # NOTE: self.install_name can be:
        #   - package name (will already be toplevel name)
        #   - path (str or pathlib.Path) to local package
        #   - url for remote install, e.g. GitHub repo (**pip only**)
        #     + if -e/--editable passed, clone and then install locally (if
        #       no local clone path provided, default to CWD)
        if config.SUPPRESS_STDOUT:
            stdout_stream = StringIO()

    def _conda_install_package(self): ...

    def exists_locally(self) -> bool: ...


def prompt_input(prompt, default=None, interrupt=None):
    # ADD DOCSTRING
    # NOTE: interrupt applies only to shell interface, not Jupyter/Colab
    response_values = {
        'yes': True,
        'y': True,
        'no': False,
        'n': False
    }
    if interrupt is not None:
        interrupt = interrupt.lower()
        if interrupt not in response_values.keys():
            raise ValueError(
                f"'interrupt' must be one of {tuple(response_values.keys())}"
            )
    if default is not None:
        default = default.lower()
        try:
            default_value = response_values[default]
        except KeyError as e:
            raise ValueError(
                f"'default' must be one of: {tuple(response_values.keys())}"
            ) from e
        response_values[''] = default_value
        opts = '[Y/n]' if default_value else '[y/N]'
    else:
        opts = '[y/n]'

    while True:
        try:
            response = input(f"{prompt}\n{opts} ").lower()
            return response_values[response]
        except KeyboardInterrupt:
            if interrupt is not None:
                return response_values[interrupt]
            else:
                raise
        except KeyError:
            pass


def run_shell_command(cmd_str):
    """
    simple helper that runs a string command in a bash shell
    and returns its exit code
    """
    return _run_shell_cmd(f"/bin/bash -c '{cmd_str}'")


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