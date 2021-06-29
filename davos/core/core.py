"""
# TODO: update me
This module contains common utilities used by by the smuggle statement
in all three environments (Python, old IPython/Google Colab, and new
IPython/Jupyter Notebook).
"""


__all__ = [
    'capture_stdout', 
    'check_conda',
    'Onion', 
    'prompt_input', 
    'run_shell_command'
]


import importlib
import itertools
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from subprocess import CalledProcessError

import pkg_resources
from packaging.requirements import InvalidRequirement

from davos import config
from davos.core.exceptions import (
    DavosError,
    InstallerError, 
    OnionParserError, 
    ParserNotImplementedError
)
from davos.core.parsers import pip_parser
# noinspection PyUnresolvedReferences
from davos.core.regexps import _pip_installed_pkgs_re, smuggle_statement_regex
# noinspection PyUnresolvedReferences
from davos.implementations import (
    _check_conda_avail_helper, 
    _run_shell_command_helper
)


class capture_stdout:
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

    def __exit__(self, exc_type, exc_value, exc_tb):
        sys.stdout.write = self.sys_stdout_write
        if self.closing:
            for s in self.streams:
                s.close()

    def _write(self, data):
        for s in self.streams:
            s.write(data)
        self.sys_stdout_write(data)
        sys.stdout.flush()


def check_conda():
    # ADD DOCSTRING
    conda_list_output = _check_conda_avail_helper()
    if conda_list_output is None:
        config._conda_avail = False
        return

    config._conda_avail = True
    # try to create mapping of environment names to paths to validate 
    # environments used in onion comments or to set config.conda_env. 
    # Want both names and paths so we can check both `-n`/`--name` & 
    # `-p`/`--prefix` when parsing onion comments
    envs_dict_command = "conda info --envs | grep -E '^\w' | sed -E 's/ +\*? +/ /g'"
    # noinspection PyBroadException
    try:
        conda_info_output = run_shell_command(envs_dict_command,
                                              live_stdout=False)
        # noinspection PyTypeChecker
        envs_dirs_dict = dict(map(str.split, conda_info_output.splitlines()))
    except Exception:
        # if no environments are found or output can't be parsed for 
        # some reason, just count any conda env provided as valid. This 
        # doesn't cause any major problems, we just can't catch errors 
        # as early and defer to the conda executable to throw an error 
        # when the user actually goes to install a package into an 
        # environment that doesn't exist.
        # (just set to None so it can be referenced down below)
        envs_dirs_dict = None

    config._conda_envs_dirs = envs_dirs_dict
    # format of first line of output seems to reliably be: `# packages 
    # in environment at /path/to/environment/dir:` but can't hurt to 
    # parse more conservatively since output is so short
    for w in conda_list_output.split():
        if '/' in w:
            env_name = w.split('/')[-1].rstrip(':')
            if (
                    envs_dirs_dict is not None and
                    env_name in envs_dirs_dict.keys()
            ):
                config._conda_env = env_name
                return

    if envs_dirs_dict is not None:
        # if we somehow fail to parse the environment directory path 
        # from the output, but we DID successfully create the 
        # environment mapping, something weird is going on and it's 
        # worth throwing an error with some info now. Otherwise, defer 
        # potential errors to conda executable
        raise DavosError(
            "Failed to programmatically determine path to conda environment "
            "directory. If you want to install smuggled packages using conda, "
            "you can either:\n\t1. set `davos.config.conda_env_path` to your "
            "environment's path (e.g., $CONDA_PREFIX/envs/this_env)\n\t2. "
            "pass the environment path to `-p`/`--prefix` in each onion "
            "comment\n\t3. pass your environment's name to `-n`/`--name` in "
            "each onion comment"
        )


def get_previously_imported_pkgs(install_cmd_stdout, installer):
    if installer == 'conda':
        raise NotImplementedError(
            "conda-install stdout parsing not implemented yet"
        )
    else:
        installed_pkg_regex = _pip_installed_pkgs_re

    matches = installed_pkg_regex.findall(install_cmd_stdout)
    if len(matches) == 0:
        return []

    # flatten and split matches to separate packages
    matches_iter = itertools.chain(*(map(str.split, matches)))
    prev_imported_pkgs = []
    for dist_name in matches_iter:
        pkg_name = dist_name.rsplit('-', maxsplit=1)[0]
        try:
            dist = pkg_resources.get_distribution(pkg_name)
        except pkg_resources.DistributionNotFound:
            # package either either new (was not previously installed) 
            # or an implicit namespace package that will show up in 
            # another package's top-level names
            continue

        try:
            toplevel_names = dist.get_metadata('top_level.txt').split()
        except FileNotFoundError:
            toplevel_names = (pkg_name,)

        for name in toplevel_names:
            if name in sys.modules:
                prev_imported_pkgs.append(name)

    return prev_imported_pkgs


def import_name(name):
    """
    Import and return a module, submodule, class, function, or other 
    object given its qualified name. 

    Parameters
    ----------
    name : `str`
        The fully qualified name of the object to import

    Returns
    -------
    `object`
        The imported object

    Notes
    -----
    This is a near-exact reimplementation of
    `IPython.utils.importstring.import_item`. The function is 
    reimplemented here to make it available in pure Python environments 
    where `IPython` may not be installed.
    """
    parts = name.rsplit('.', maxsplit=1)
    if len(parts) == 2:
        mod_name, obj_name = parts
        # built-in __import__ should be faster than importlib.__import__
        module = __import__(mod_name, fromlist=[obj_name])
        try:
            obj = getattr(module, obj_name)
        except AttributeError as e:
            raise ImportError(
                f'No object or submodule "{obj_name}" found in module '
                f'"{mod_name}"'
            ) from e
        return obj
    else:
        return __import__(parts[0])


class Onion:
    # ADD DOCSTRING
    @staticmethod
    def parse_onion(onion_text):
        onion_text = onion_text.lstrip('# ')
        installer, args_str = onion_text.split(':', maxsplit=1)
        # normalize whitespace
        installer = installer.strip()
        args_str = ' '.join(args_str.split()).strip()
        # regex parsing to identify onion comments already ensures the
        # comment will start with "<installer>:"
        if installer == 'pip':
            parser = pip_parser
        elif installer == 'conda':
            msg = "smuggling packages via conda is not yet supported"
            raise ParserNotImplementedError(
                msg, target_text=onion_text,
                target_offset=onion_text.index('conda')
            )
        else:
            # theoretically not possible to get here given regex parser,
            # but include as a failsafe for completeness
            msg = ("An unexpected error occurred while trying to parse onion "
                   f"comment: {onion_text}")
            raise OnionParserError(msg, target_text=onion_text)
        installer_kwargs = vars(parser.parse_args(args_str.split()))
        # arg_str could potentially have both single and double quotes
        # in it, so triple quote to be safe
        return f'"{installer}"', f'"""{args_str}"""', installer_kwargs

    def __init__(self, package_name, installer, args_str, **installer_kwargs):
        # ADD DOCSTRING
        self.import_name = package_name
        self.installer = installer
        if installer == 'pip':
            self.install_package = self._pip_install_package
        elif installer == 'conda':
            raise NotImplementedError(
                "smuggling packages via conda is not yet supported"
            )
        else:
            # here to handle user calling smuggle() *function* directly
            raise InstallerError(
                f"Unsupported installer: '{installer}'. Currently supported "
                "installers are:\n\t'pip'"  # and 'conda'"
            )
        self.build = None
        self.args_str = args_str
        self.cache_key = f"{installer};{';'.join(args_str.split())}"
        if args_str == '':
            # bare smuggle statement without onion comment
            self.is_editable = False
            self.verbosity = 0
            self.installer_kwargs = {}
            self.install_name = package_name
            self.version_spec = ''
            return
        full_spec = installer_kwargs.pop('spec').strip("'\"")
        self.is_editable = installer_kwargs.pop('editable')
        self.verbosity = installer_kwargs.pop('verbosity', 0)
        self.installer_kwargs = installer_kwargs
        if '+' in full_spec:
            # INSTALLING FROM LOCAL/REMOTE VCS:
            #   self.install_name is the VCS program + '+' + absolute
            #   local path or remote URL, plus any optional fields
            #   (#egg=..., [#|&]subdirectory=...) except for @<ref>
            #   specifier, which is used as self.version_spec if present

            # parse out <ref> without affecting setuptools extras syntax
            _before, _sep, _after = full_spec.rpartition('@')
            if '+' in _before:
                # @<ref> was present and we split there. Get everything
                # up to #egg=..., #subdirectory=..., or end of spec
                ver_spec = _after.split('#')[0]
                # self.install_name is full spec with @<ref> removed
                self.install_name = full_spec.replace(f'@{ver_spec}', '')
                self.version_spec = f'=={ver_spec}'
            else:
                # @ either not present or used only for setuptools extra
                self.install_name = full_spec
                self.version_spec = ''
        elif '/' in full_spec:
            # INSTALLING FROM LOCAL PROJECT OR PEP 440 DIRECT REFERENCE:
            #   self.install_name is the absolute path to a local
            #   project or source archive, or the URL for a remote source
            #   archive
            self.install_name = full_spec
            self.version_spec = ''
        else:
            # INSTALLING USING A REQUIREMENT SPECIFIER:
            #   most common usage. self.install_name is package name
            #   provided in onion comment. self.version_spec is
            #   (optional) version specifier

            # split on ',' to handle multiple specs ('pkg>=1.0,<=2.0')
            first_subspec = full_spec.split(',')[0]
            for spec_delim in ('==', '<=', '>=', '!=', '~=', '<', '>', '='):
                if spec_delim in first_subspec:
                    self.install_name = full_spec[:full_spec.index(spec_delim)]
                    ver_spec = full_spec[full_spec.index(spec_delim):]
                    # if (
                    #         installer == 'conda' and
                    #         '=' in ver_spec[len(spec_delim):]
                    # ):
                    #     # if conda-installing specific build of package,
                    #     # separate build version from package version
                    #     # and handle independently
                    #     ver_spec, build = ver_spec.rsplit('=', maxsplit=1)
                    self.version_spec = ver_spec
                    break
            else:
                # no version specified with package name
                self.install_name = full_spec
                self.version_spec = ''

    @property
    def install_cmd(self):
        if self.args_str == '':
            args = self.install_name
        else:
            args = self.args_str.replace("<", "'<'").replace(">", "'>'")
        if self.installer == 'pip':
            install_exe = config._pip_executable
        else:
            install_exe = self.installer

        return f'{install_exe} install {args}'

    @property
    def is_installed(self):
        installer_kwargs = self.installer_kwargs
        if self.import_name in config._stdlib_modules:
            # smuggled module is part of standard library
            return True
        elif (
                installer_kwargs.get('force_reinstall') or
                installer_kwargs.get('ignore_installed') or
                installer_kwargs.get('upgrade')
        ):
            # args that trigger install regardless of installed version
            return False
        elif self.args_str == config._smuggled.get(self.cache_key):
            # if the same version of the same package was smuggled from
            # the same source with all the same arguments previously in
            # the current interpreter session/notebook runtime (i.e.,
            # line is just being rerun)
            return True
        elif '/' not in self.install_name:
            full_spec = self.install_name + self.version_spec.replace("'", "")
            try:
                pkg_resources.get_distribution(full_spec)
            except pkg_resources.DistributionNotFound:
                # noinspection PyUnresolvedReferences
                # suppressed due to issue with importlib stubs in 
                # typeshed repo
                module_spec = importlib.util.find_spec(self.import_name)
                if module_spec is None:
                    # requested package is not installed
                    return False
                else:
                    # requested package is a namespace package
                    return True
            except (
                # package is installed, but installed version doesn't
                # fit requested version constraints
                pkg_resources.VersionConflict,
                # version_spec is invalid or pkg_resources couldn't
                # parse it
                InvalidRequirement
            ):
                return False
            else:
                return True
        return False

    def _conda_install_package(self):
        raise NotImplementedError(
            "smuggling packages via conda is not yet supported"
        )

    def _pip_install_package(self):
        live_stdout = self.verbosity > -3
        try:
            stdout = run_shell_command(self.install_cmd, live_stdout=live_stdout)
        except CalledProcessError as e:
            err_msg = (f"the command '{e.cmd}' returned a non-zero "
                       f"exit code: {e.returncode}. See above output "
                       f"for details")
            raise InstallerError(err_msg, e)
        # handle packages installed in non-standard locations
        install_dir = self.installer_kwargs.get('target')
        if install_dir is not None and install_dir not in sys.path:
            # make sure alternate target directory is in the module
            # search path so import machinery will find it
            sys.path.insert(0, install_dir)
        elif self.is_editable:
            install_dir = self.installer_kwargs.get('src')
            if install_dir is not None:
                # passing --src only affects editable VCS installs,
                # which are guaranteed to have #egg=<pkg_name>
                proj_name = self.install_name.split('#egg=')[1]
                # get rid of any quotes used to escape operators
                proj_name = proj_name.replace('"', '').replace("'", "")
                # only thing #egg=<pkg_name> may be followed by is
                # &subdirectory=<subdirectory>
                proj_name, _, subdir_name = proj_name.partition('&subdirectory=')
                # pip converts underscores to hyphens when naming dir
                proj_name = proj_name.replace('_', '-')
                install_dir = Path(install_dir).resolve().joinpath(proj_name,
                                                                   subdir_name)
                if install_dir not in sys.path:
                    sys.path.insert(0, str(install_dir))
        return stdout


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


def run_shell_command(command, live_stdout=None):
    # ADD DOCSTRING
    if live_stdout is None:
        live_stdout = not config._suppress_stdout
    if live_stdout:
        command_context = capture_stdout
    else:
        command_context = redirect_stdout
    with command_context(StringIO()) as stdout:
        try:
            _run_shell_command_helper(command)
        except CalledProcessError as e:
            # if the exception doesn't record the output, add it
            # manually before raising
            stdout = stdout.getvalue()
            if e.output is None and stdout != '':
                e.output = stdout
            raise e
        else:
            stdout = stdout.getvalue()
    return stdout


def smuggle(
        name, 
        as_=None, 
        installer='pip', 
        args_str='', 
        installer_kwargs=None
):
    # ADD DOCSTRING
    if installer_kwargs is None:
        installer_kwargs = {}

    pkg_name = name.split('.')[0]
    onion = Onion(pkg_name, installer=installer,
                  args_str=args_str, **installer_kwargs)

    if onion.is_installed:
        try:
            # Unlike regular import, can be called on non-module items:
            #     ```
            #     import numpy.array`                   # fails
            #     array = import_item('numpy.array')    # succeeds
            #     ```
            # Also adds module (+ parents, if any) to sys.modules if not
            # already present.
            smuggled_obj = import_name(name)
        except ModuleNotFoundError as e:
            # TODO: check for --yes (conda) and bypass if passed
            if config._confirm_install:
                msg = (f"package '{pkg_name}' will be installed with the "
                       f"following command:\n\t`{onion.install_cmd}`\n"
                       f"Proceed?")
                install_pkg = prompt_input(msg, default='y')
                if not install_pkg:
                    raise e
            else:
                install_pkg = True
        else:
            install_pkg = False
    else:
        install_pkg = True

    if install_pkg:
        installer_stdout = onion.install_package()
        # check whether the smuggled package and/or any installed/updated
        # dependencies were already imported during the current runtime
        prev_imported_pkgs = get_previously_imported_pkgs(installer_stdout, 
                                                          onion.installer)
        # invalidate sys.meta_path module finder caches. Forces import
        # machinery to notice newly installed module
        importlib.invalidate_caches()
        # if the smuggled package was previously imported, deal with
        # it last so it's reloaded after its dependencies are in place
        try:
            prev_imported_pkgs.remove(pkg_name)
        except ValueError:
            # smuggled package is brand new
            pass
        else:
            prev_imported_pkgs.append(pkg_name)

        failed_reloads = []
        for dep_name in prev_imported_pkgs:
            dep_modules_old = {}
            for mod_name in tuple(sys.modules.keys()):
                # remove submodules of previously imported packages so
                # new versions get imported when main package is
                # reloaded (importlib.reload only reloads top-level
                # module). IPython.lib.deepreload.reload recursively
                # reloads submodules, but is basically broken because
                # it's *too* aggressive. It reloads *all* imported
                # modules... including the import machinery it needs to
                # run, which crashes it... (-_-* )
                if mod_name.startswith(f'{dep_name}.'):
                    dep_modules_old[mod_name] = sys.modules.pop(mod_name)

            # get (but don't pop) top-level package to that it can be
            # reloaded (must exist in sys.modules)
            dep_modules_old[dep_name] = sys.modules[dep_name]
            try:
                importlib.reload(sys.modules[dep_name])
            except (ImportError, ModuleNotFoundError, RuntimeError):
                # if we aren't able to reload the module, put the old
                # version's submodules we removed back in sys.modules
                # for now and prepare to show a warning post-execution.
                # This way:
                #   1. the user still has a working module until they
                #      restart the runtime
                #   2. the error we got doesn't keep getting raised when
                #      we try to reload/import other modules that
                #      import it
                sys.modules.update(dep_modules_old)
                failed_reloads.append(dep_name)

        if any(failed_reloads):
            # packages with C extensions (e.g., numpy, pandas) cannot be
            # reloaded within an interpreter session. If the package was
            # previously imported in the current runtime (even if not by
            # user), warn about needing to reset runtime for changes to
            # take effect with "RESTART RUNTIME" button in output
            # (doesn't raise an exception, remaining code in cell still
            # runs)
            _display_mimetype(
                "application/vnd.colab-display-data+json",
                (
                    {'pip_warning': {'packages': ', '.join(failed_reloads)}},
                ),
                raw=True
            )
        smuggled_obj = import_name(name)
        # finally, reload pkg_resources so that just-installed package
        # will be recognized when querying local versions for later
        # checks
        importlib.reload(sys.modules['pkg_resources'])

    # add the object name/alias to the notebook's global namespace
    if as_ is None:
        config.ipython_shell.user_ns[name] = smuggled_obj
    else:
        config.ipython_shell.user_ns[as_] = smuggled_obj
    # cache the smuggled (top-level) package by its full onion comment
    # so rerunning cells is more efficient, but any change to version,
    # source, etc. is caught
    config.smuggled[pkg_name] = onion.cache_key


# noinspection DuplicatedCode
def parse_line(line):
    # ADD DOCSTRING
    match = smuggle_statement_regex.match(line)
    if match is None:
        return line

    matched_groups = match.groupdict()
    smuggle_chars = matched_groups['FULL_CMD']
    before_chars, after_chars = line.split(smuggle_chars)
    cmd_prefix, to_smuggle = smuggle_chars.split('smuggle ', maxsplit=1)
    cmd_prefix = cmd_prefix.strip()
    to_smuggle = to_smuggle.strip()

    if cmd_prefix:
        # cmd_prefix is `"from" package[.module[...]] `
        is_from_statement = True
        onion_chars = matched_groups['FROM_ONION'] or matched_groups['FROM_ONION_1']
        has_semicolon_sep = matched_groups['FROM_SEMICOLON_SEP'] is not None
        qualname_prefix = f"{''.join(cmd_prefix.split()[1:])}."
        # remove parentheses around line continuations
        to_smuggle = to_smuggle.replace(')', '').replace('(', '')
        # remove inline comments
        if '\n' in to_smuggle:
            to_smuggle = ' '.join(l.split('#')[0] for l in to_smuggle.splitlines())
        else:
            to_smuggle = to_smuggle.split('#')[0]
        # normalize whitespace
        to_smuggle = ' '.join(to_smuggle.split()).strip(', ')
    else:
        # cmd_prefix is ''
        is_from_statement = False
        onion_chars = matched_groups['ONION']
        has_semicolon_sep = matched_groups['SEMICOLON_SEP'] is not None
        qualname_prefix = ''

    kwargs_str = ''
    if has_semicolon_sep:
        after_chars = '; ' + parse_line(after_chars.lstrip('; '))
    elif onion_chars is not None:
        onion_chars = onion_chars.replace('"', "'")
        to_smuggle = to_smuggle.replace(onion_chars, '').rstrip()
        # `Onion.parse_onion()` returns a 3-tuple of:
        #  - the installer name (str)
        #  - the raw arguments to be passed to the installer (str)
        #  - an {arg: value} mapping from parsed args & defaults (dict)
        installer, args_str, installer_kwargs = Onion.parse_onion(onion_chars)
        kwargs_str = (f', installer={installer}, '
                      f'args_str={args_str}, '
                      f'installer_kwargs={installer_kwargs}')

    smuggle_funcs = []
    names_aliases = to_smuggle.split(',')
    for na in names_aliases:
        if ' as ' in na:
            name, alias = na.split(' as ')
            name = f'"{qualname_prefix}{name}"'
            alias = f'"{alias.strip()}"'
        else:
            name = f'"{qualname_prefix}{na}"'
            alias = f'"{na.strip()}"' if is_from_statement else None

        name = name.replace(' ', '')
        smuggle_funcs.append(f'smuggle(name={name}, as_={alias})')

    smuggle_funcs[0] = smuggle_funcs[0][:-1] + kwargs_str + ')'
    return before_chars + '; '.join(smuggle_funcs) + after_chars
