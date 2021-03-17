# will hold functions used by all 3 approaches, helper functions, etc.
# once other 2 smugglers are written


import sys
from contextlib import redirect_stdout
from io import StringIO

from davos import config
from davos.exceptions import InstallerError, OnionSyntaxError

if config.IPYTHON_SHELL is not None:
    from IPython.core.interactiveshell import system as _run_shell_cmd


class Onion:
    # ADD DOCSTRING
    @staticmethod
    def extract_arg_value(arg_name, args_str):
        # NOTE: does not handle args with multiple space-separated values
        if arg_name not in args_str:
            return None, args_str
        pre, post = args_str.split(arg_name)
        pre = pre.strip()
        post = post.strip()
        arg_val, _, post = post.partition(' ')[0]
        if arg_val.startswith('-') or arg_val == '':
            raise OnionSyntaxError(f"'{arg_name}' flag requires an argument")
        new_args_str = ' '.join((pre, post))
        return arg_val, new_args_str

    @staticmethod
    def parse_onion_syntax(comment_text):
        # TODO: parse comment string for install arguments, use
        #  https://github.com/ContextLab/CDL-docker-stacks/blob/master/CI/conda_environment.py#L56-L65
        #  for splitting version string
        # TODO: handle scenario where it's an unrelated, non-onion
        #  comment
        # TODO: if install_name is a VCS url, explicitly look for --egg
        #  and --subdirectory in comment_text to make full URL for pip
        # NOTE: returns a dict of {param: value} for each, CLI args that
        #  don't take a value should be ... so they don't
        #  conflict with None values in constructor
        peeled_onion = {
            'installer': 'pip',
            'install_name': None,
            'version_spec': None,
            'egg': None,
            'subdirectory': None
        }
        comment_text = comment_text.strip()
        installer, sep, arg_str = comment_text.parition(':')
        if installer == 'conda':
            peeled_onion['installer'] = 'conda'
        elif installer != 'pip' and installer != 'pypi':
            # unrelated, non-onion inline comment
            return peeled_onion
        if sep == '':
            # no colon, no install arguments other than installer name
            return peeled_onion

        version_spec, _, arg_str = arg_str.strip().partition(' ')
        # split on ',' to account for 'pkg>=1.0,<=2.0' syntax
        first_subspec = version_spec.split(',')[0]
        for spec_delim in ('==', '<=', '>=', '!=', '~=', '<', '>', '='):
            if spec_delim in first_subspec:
                inst_name = version_spec[:version_spec.index(spec_delim)]
                ver_spec = version_spec[version_spec.index(spec_delim):]
                break
        else:
            # either no version specified or installing from VCS, local
            # project, local/remote archive, wheel file, etc.
            ver_spec = None
            inst_name = version_spec
            if '+' in version_spec:
                # installing from VCS (e.g., git+https://...) requires
                # special handling of --egg & --subdirectory arguments
                # that would normally be part of URL but can't due to
                # Onion format
                egg_name, arg_str = Onion.extract_arg_value('--egg', arg_str)
                peeled_onion['egg'] = egg_name
                subdir_path, arg_str = Onion.extract_arg_value('--subdirectory',
                                                               arg_str)
                peeled_onion['subdirectory'] = subdir_path
        peeled_onion['install_name'] = inst_name
        peeled_onion['version_spec'] = ver_spec
        return peeled_onion

    def __init__(self, import_name, installer='pip', install_name=None,
                 version_spec=None, egg=None, subdirectory=None,
                 **installer_kwargs):
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
        #     + if -e/--editable passed, clone and then install locally
        #       (if no local clone path provided, default to CWD)
        # TODO: would be more efficient to use nullcontext here as long
        #  as it works in ipynb
        # TODO: add support for all kinds of non-index installs (see
        #  https://pip.pypa.io/en/stable/reference/pip_install/)
        cli_args = self._fmt_installer_args()
        cmd_str = f'pip install {cli_args} {self.install_name}'
        if config.SUPPRESS_STDOUT:
            stdout_stream = StringIO()
        else:
            stdout_stream = sys.stdout
        with redirect_stdout(stdout_stream):
            exit_code = run_shell_command(cmd_str)
        if exit_code != 0:
            if config.SUPPRESS_STDOUT:
                sys.stderr.write(stdout_stream.getvalue().strip())
                err_msg = (f"the command '{cmd_str}' returned a non-zero exit "
                           f"code: {exit_code}. See above output for details")
                raise InstallerError(err_msg)


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