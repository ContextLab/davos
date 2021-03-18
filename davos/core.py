# will hold functions used by all 3 approaches, helper functions, etc.
# once other 2 smugglers are written


import sys
from contextlib import redirect_stdout
from io import StringIO

from packaging.specifiers import Specifier

from davos import davos
from davos.exceptions import InstallerError, OnionSyntaxError

if davos.ipython_shell is not None:
    from IPython.core.interactiveshell import system as _run_shell_cmd
    def run_shell_command(cmd_str):
        #runs a string command in a bash shell and returns its exit code
        return _run_shell_cmd(f"/bin/bash -c '{cmd_str}'")


class Onion:
    # ADD DOCSTRING
    @staticmethod
    def _extract_arg_value(arg_name, args_str):
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
        # TODO: replace short arg versions with long versions to account
        #  for combinations, e.g. `pip install -UIt <target> package`
        # NOTE: returns a dict of {param: value} for each, CLI args that
        #  don't take a value should be ... so they don't
        #  conflict with None values in constructor
        # minimal fields that should always be in returned dict
        peeled_onion = {
            'installer': 'pip',
            'installer_args': ''
            # 'install_name': None,
            # 'version_spec': None,
            # 'egg': None,
            # 'subdirectory': None,
            # 'build': None
        }
        comment_text = comment_text.strip()
        installer, sep, arg_str = comment_text.partition(':')
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
                if installer == 'conda' and '=' in ver_spec[len(spec_delim):]:
                    # if conda-installing specific build of package,
                    # separate build version from package version and
                    # handle independently
                    ver_spec, build = ver_spec.rsplit('=', maxsplit=1)
                    peeled_onion['build'] = build
                break
        else:
            # either no version specified or installing from VCS, local
            # project, local/remote archive, wheel file, etc.
            ver_spec = None
            inst_name = version_spec
            if '+' in version_spec:
                # pip-installing from VCS (e.g., git+https://...)
                # requires special handling of --egg & --subdirectory
                # arguments that would normally be part of URL but can't
                # due to Onion format
                egg_name, arg_str = Onion._extract_arg_value('--egg', arg_str)
                subdir_path, arg_str = Onion._extract_arg_value('--subdirectory',
                                                               arg_str)
                peeled_onion['egg'] = egg_name
                peeled_onion['subdirectory'] = subdir_path
        peeled_onion['install_name'] = inst_name
        peeled_onion['version_spec'] = ver_spec
        peeled_onion['installer_args'] = arg_str
        return peeled_onion

    def __init__(self, import_name, installer='pip', install_name=None,
                 version_spec=None, build=None, egg=None, subdirectory=None,
                 installer_args=''):
        # ADD DOCSTRING
        # TODO: what happens if force-reinstall, ignore-installed, etc.
        #  and module is already in sys.modules?
        if installer == 'pip' or installer == 'pypi':
            self.install_package = self._pip_install_package
        elif installer == 'conda':
            self.install_package = self._conda_install_package
        else:
            # here to handle user calling smuggle() *function* directly
            raise InstallerError(
                f"Unsupported installer: '{installer}'. Currently supported "
                "installers are 'pip' and 'conda'"
            )
        self.installer = installer
        if install_name is None:
            self.install_name = import_name
        else:
            self.install_name = install_name
        self.version_spec = version_spec
        self.build = build
        self.egg = egg
        self.subdirectory = subdirectory
        self.installer_args = installer_args

    @property
    def is_installed(self):
        # TODO: generalize this to use pip show or conda list
        # TODO: currently, previously-installed VCS, local, etc.
        #  packages will always be re-installed... how to better handle
        #  this?
        if self.install_name in davos.smuggled:
            return True
        elif ('--force-reinstall' in self.installer_args or
              '--ignore-installed' in self.installer_args or
              '--upgrade' in self.installer_args or
              '+' in self.install_name):
            return False
        else:
            pip_show_output = StringIO()
            with redirect_stdout(pip_show_output):
                exit_code = run_shell_command(f'pip show {self.install_name}')
            if exit_code == 1:
                return False
            elif self.version_spec is None:
                return True
            else:
                pip_show_output = pip_show_output.getvalue()
                try:
                    version_line = next(l for l in pip_show_output
                                        if l.startswith('version:'))
                except StopIteration:
                    # this should never happen, but default to
                    # installing if version isn't listed in output
                    return False
                else:
                    version = version_line.split(': ')[1]
                    specifier = Specifier(self.version_spec)
                    return specifier.contains(version)

    def _pip_install_package(self):
        # TODO: would be more efficient to use nullcontext here as long
        #  as it works in ipynb
        # TODO: add support for all kinds of non-index installs (see
        #  https://pip.pypa.io/en/stable/reference/pip_install/)
        install_name = self.install_name
        if '+' in install_name:
            vcs_field_sep= '#'
            if self.egg is not None:
                install_name += vcs_field_sep + self.egg
                vcs_field_sep = '&'
            if self.subdirectory is not None:
                install_name += vcs_field_sep + self.subdirectory
        elif self.version_spec is not None:
            install_name += self.version_spec
        cmd_str = f'pip install {self.installer_args} {install_name}'
        if davos.suppress_stdout:
            stdout_stream = StringIO()
        else:
            stdout_stream = sys.stdout
        with redirect_stdout(stdout_stream):
            exit_code = run_shell_command(cmd_str)
        if exit_code != 0:
            if davos.suppress_stdout:
                sys.stderr.write(stdout_stream.getvalue().strip())
                err_msg = (f"the command '{cmd_str}' returned a non-zero exit "
                           f"code: {exit_code}. See above output for details")
                raise InstallerError(err_msg)

    def _conda_install_package(self):
        raise NotImplementedError


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