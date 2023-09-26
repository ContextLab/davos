"""
Davos core functionality and utilities.

This module implements core elements of davos's functionality and
various utilities that are common across the various
environment-specific implementations. This includes parsing user code to
extract `smuggle` statements and Onion comments, parsing their contents,
searching the local package environment, installing missing packages,
loading them into the user's namespace, and more.
"""


# pylint: disable=too-many-lines
__all__ = [
    'capture_stdout',
    'check_conda',
    'get_previously_imported_pkgs',
    'handle_alternate_pip_executable',
    'import_name',
    'Onion',
    'parse_line',
    'prompt_input',
    'run_shell_command',
    'use_project',
    'smuggle'
]


import functools
import importlib
import itertools
import sys
import warnings
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from pathlib import Path
from subprocess import CalledProcessError

from packaging.requirements import InvalidRequirement
from packaging.specifiers import SpecifierSet
if sys.version_info < (3, 8):
    import importlib_metadata as metadata
else:
    from importlib import metadata

from davos import config
from davos.core.exceptions import (
    DavosError,
    InstallerError,
    OnionArgumentError,
    OnionParserError,
    ParserNotImplementedError,
    SmugglerError,
    TheNightIsDarkAndFullOfErrors
)
from davos.core.parsers import pip_parser
from davos.core.regexps import (
    pip_installed_pkgs_regex,
    smuggle_statement_regex
)
# noinspection PyUnresolvedReferences
from davos.implementations import (
    _check_conda_avail_helper,
    _run_shell_command_helper,
    auto_restart_rerun,
    prompt_restart_rerun_buttons
)


class capture_stdout:    # pylint: disable=invalid-name
    """
    Context manager for sending stdout to multiple streams at once.

    Similar to `contextlib.redirect_stdout`, but different in that it:
      - temporarily writes stdout to other streams *in addition to*
        rather than *instead of* `sys.stdout`
      - accepts any number of streams and sends stdout to each
      - can optionally keep streams open after exiting context by
        passing `closing=False`

    Works by temporarily replacing `sys.stdout`'s `write` method with
    its own `_write` method, which writes the received data to all
    provided streams in addition to `sys.stdout`.
    """

    def __init__(self, *streams, closing=True):
        """
        Parameters
        ----------
        *streams : tuple of io.TextIOBase
            I/O stream(s) to receive data sent to `sys.stdout`. Must be
            subclasses of `io.TextIOBase` (i.e., support reading/writing
            `str` data, rather than `bytes`).
        closing : bool, optional
            if `True` (default), close streams upon exiting the context
            block.
        """
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
            for stream in self.streams:
                stream.close()

    def _write(self, data):
        for stream in self.streams:
            stream.write(data)
        self.sys_stdout_write(data)
        sys.stdout.flush()


def check_conda():
    """
    Check whether conda is installed and get environment info, if so.

    Called lazily to set values for `conda_avail`, `conda_env`, and
    `conda_envs_dirs` config fields. Checks whether the conda executable
    is available by running `conda list IPython` (via environment-
    dependent `_check_conda_avail_helper()` function). If successful,
    parses command output for name of active conda environment. Also
    parses {env_name: env_path} mapping of all available environments
    from the output of `conda info --envs`.

    Raises
    ------
    DavosError
        If the environment mapping could be parsed from the output of
        `conda info --envs`, but the active environment name couldn't be
        parsed from the output of `conda list IPython`
    """
    conda_list_output = _check_conda_avail_helper()
    if conda_list_output is None:
        config._conda_avail = False
        return

    config._conda_avail = True
    # try to create mapping of environment names to paths to validate
    # environments used in onion comments or to set config.conda_env.
    # Want both names and paths so we can check both `-n`/`--name` &
    # `-p`/`--prefix` when parsing onion comments
    envs_dict_command = r"conda info --envs | grep -E '^\w' | sed -E 's/ +\*? +/ /g'"
    # noinspection PyBroadException
    try:
        conda_info_output = run_shell_command(envs_dict_command,
                                              live_stdout=False)
        # noinspection PyTypeChecker
        envs_dirs_dict = dict(map(str.split, conda_info_output.splitlines()))
    except Exception:    # pylint: disable=broad-except
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
    for word in conda_list_output.split():
        if '/' in word:
            env_name = word.split('/')[-1].rstrip(':')
            if (
                    envs_dirs_dict is not None and
                    env_name not in envs_dirs_dict.keys()
            ):
                continue
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
            "you can either:\n\t1. set `davos.conda_env_path` to your "
            "environment's path (e.g., $CONDA_PREFIX/envs/this_env)\n\t2. "
            "pass the environment path to `-p`/`--prefix` in each onion "
            "comment\n\t3. pass your environment's name to `-n`/`--name` in "
            "each onion comment"
        )


def get_previously_imported_pkgs(install_cmd_stdout, installer):
    """
    Get just-installed packages previously imported by the interpreter.

    Parses stdout from installing a smuggled package for the names of
    all packages/dependencies that were installed or upgraded. Then,
    converts these "install names" (e.g., `scikit-learn`) to "import
    names" (e.g., `sklearn`) and checks for them in `sys.modules`.
    Returns the list import names found.

    Parameters
    ----------
    install_cmd_stdout : str
        Captured stdout generated by the smuggled package's installation
    installer : {'pip', 'conda'}
        The name of the program that generated the output to be parsed

    Returns
    -------
    list of str
        Names of packages installed/upgraded when installed the smuggled
        package that were previously imported by the current interpreter

    See Also
    --------
    google.colab._pip._previously_imported_packages :
        https://github.com/googlecolab/colabtools/blob/2211417/google/colab/_pip.py#L93

    Notes
    -----
    - Functionally, this is a reimplementation of `colabtools`'s
      `google.colab._pip._previously_imported_packages()`. This version
      has some minor tweaks that make it more efficient, but is mostly
      meant to be available when `colabtools` may not be installed
      (i.e., outside of Colaboratory).
    - There's an edge case neither this nor `colabtools`'s version
      handles: if the user passes -q/--quiet 3x to the pip-install
      command, there will be no stdout to parse.
    """
    if installer == 'conda':
        raise NotImplementedError(
            "conda-install stdout parsing is not yet implemented"
        )
    installed_pkg_regex = pip_installed_pkgs_regex

    matches = installed_pkg_regex.findall(install_cmd_stdout)
    if len(matches) == 0:
        return []

    # flatten and split matches to separate packages
    matches_iter = itertools.chain(*(map(str.split, matches)))
    prev_imported_pkgs = []
    # install command's stdout contains install names (e.g.,
    # scikit-learn), but we need import names (e.g., sklearn).
    for dist_name in matches_iter:
        # get the install name without the version
        pkg_name = dist_name.rsplit('-', maxsplit=1)[0]
        # use the install name to get the package distribution object
        dist = metadata.distribution(pkg_name)
        # check the distribution's metadata for a file containing
        # top-level import names. Also includes names of namespace
        # packages (e.g. mpl_toolkits from matplotlib), if any.
        toplevel_names = dist.read_text('top_level.txt')
        if toplevel_names is None:
            # importlib.metadata.PathDistribution.read_text() suppresses
            # FileNotFoundError (also IsADirectoryError, KeyError,
            # NotADirectoryError, and PermissionError), so if
            # toplevel_names is None, top_level.txt doesn't exist and
            # the import name is the install name
            toplevel_names = (pkg_name,)
        else:
            # file contains one name per line (with trailing newline)
            toplevel_names = toplevel_names.split()

        for name in toplevel_names:
            if name in sys.modules:
                prev_imported_pkgs.append(name)

    return prev_imported_pkgs


@contextmanager
def handle_alternate_pip_executable(installed_name):
    """
    Load packages installed outside of the typical module search path.

    Context manager that makes it possible to load packages installed
    into a different Python environment by changing the `pip` executable
    (`davos.pip_executable`). This is done by using the `pip` executable
    with which the package was installed to determine its location, and
    then temporarily prepending that location to the module search path.

    Parameters
    ----------
    installed_name : str
        Package name as passed to the `pip install` command. This is the
        value of self.install_name for the Onion object for the
        just-installed package.

    Notes
    -----
    Super-duper edge case not handled by this: user has used alternate
    pip_executable to smuggle local package from CWD and supplies
    relative path in onion comment (i.e., "# pip: . <args>").
    """
    if '/' in installed_name:
        # handle local paths, local/remote VCS, PEP 440 direct ref, etc.
        dist_name = installed_name.split('@')[0].split('#')[0].split('/')[-1]
    else:
        # common case
        dist_name = installed_name

    # get install location from `pip show ___` command.
    # In most cases, this will be `davos.pip_executable` with
    # trailing 'bin/pip' replaced with python<major.minor>/site-packages
    # but since this runs only if non-default pip_executable is set,
    # it's worth the extra run time to check the safer way in order to
    # handle various edge cases (e.g., installing from VCS, etc.)
    pip_show_cmd = f'{config._pip_executable} show {dist_name}'
    try:
        pip_show_stdout = run_shell_command(pip_show_cmd, live_stdout=False)
        location_line = next(
            l for l in pip_show_stdout.strip().splitlines()
            if l.startswith('Location')
        )
    except (CalledProcessError, StopIteration) as e:
        msg = (
            "Unable to locate package installed installed with non-default "
            f"'pip' executable: {dist_name}. Package has been successfully "
            "installed but not loaded."
        )
        raise SmugglerError(msg) from e

    install_location = location_line.split(': ', maxsplit=1)[1].strip()
    sys.path.insert(0, install_location)
    try:
        yield
    finally:
        # remove temporary dir from path
        sys.path.remove(install_location)


def import_name(name):
    """
    Import an object by its qualified name.

    Can be used to load a module, submodule, class, function, or other
    object, including in situations where the regular `import` statement
    would fail.

    Parameters
    ----------
    name : str
        The fully qualified name of the object to import

    Returns
    -------
    object
        The imported object

    See Also
    --------
    IPython.utils.importstring.import_item :
        https://github.com/ipython/ipython/blob/b3355a9/IPython/utils/importstring.py#L10

    Notes
    -----
    This is a near-exact reimplementation of
    `IPython.utils.importstring.import_item`. This version exists to
    make it available in pure Python environments where `IPython` may
    not be installed.
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
                f'No module or object "{obj_name}" found in "{mod_name}"'
            ) from e
        return obj
    return __import__(parts[0])


class Onion:
    """
    Class representing a single package to be smuggled.

    Naturally, "`davos`" smuggles "`Onion`s" [1]. Internally, each
    `smuggle` statement (with or without an "onion comment") creates an
    `Onion` instance, which contains all the information necessary to
    import and, if necessary, install it.

    See Also
    --------
    [1] https://en.wikipedia.org/wiki/Davos_Seaworth
    """

    @staticmethod
    def parse_onion(onion_text):
        """
        Parse the installer name and arguments from an onion comment.

        Parameters
        ----------
        onion_text : str
            An onion comment, including the leading "#".

        Returns
        -------
        str
            The installer name, enclosed in double quotes.
        str
            The raw arguments to be passed to the installer, enclosed in
            triple-double quotes.
        dict
            Argument names and values parsed from the raw argument
            string (2nd item in returned tuple), supplemented by default
            values.
        """
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
        """
        Parameters
        ----------
        package_name : str
            The name of the package or top-level module to be smuggled.
        installer : {'pip', 'conda'}
            The name of the program used to install the package if a
            compatible distribution (package name, version, build, etc.)
            cannot be found locally.
        args_str : str
            Raw arguments (taken from an onion comment, if provided) to
            be passed to the `installer` program's "install" command.
        **installer_kwargs : dict, optional
            Additional argument values to be passed to the installer.
        """
        self.import_name = package_name
        self.installer = installer
        if installer == 'pip':
            self.install_package = self._pip_install_package
            self.build = None
        elif installer == 'conda':
            raise NotImplementedError(
                "smuggling packages via conda is not yet supported"
            )
        else:
            # here to handle user calling smuggle() *function* directly
            raise OnionParserError(
                f"Unsupported installer: {installer!r}. Currently supported "
                "installers are:\n\t'pip'"  # and 'conda'"
            )
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
        if config._project is not None and (
            # for this few checks, `or` is ~3x faster than `any()` and
            # ~2x faster than `set.intersection()`
            'target' in installer_kwargs or
            'user' in installer_kwargs or
            'root' in installer_kwargs or
            'prefix' in installer_kwargs
        ):
            # when using a davos Project, pip-install arguments that
            # install the package into a different location are
            # disallowed. This check needs to happen at runtime rather
            # than during the parsing stage in case `davos.project` is
            # set/changed in the same cell as the `smuggle` statement.
            msg = (
                "When using a davos Project to isolate smuggled packages, "
                "pip-install arguments that change the package's install "
                "location (`-t/--target`, `--user`, `--root`, `--prefix`) "
                "are disallowed. To disable davos project isolation, set "
                "`davos.project = None`."
            )
            bad_arg = next(arg for arg in ('target', 'user', 'root', 'prefix')
                           if arg in installer_kwargs)
            if bad_arg == 'target':
                bad_arg = '-t/--target'
            else:
                bad_arg = f'--{bad_arg}'
            raise OnionArgumentError(msg, argument=bad_arg)
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
                # up to #egg=..., #subdirectory=..., or end of spec, and
                # add '@' back to spec
                ver_spec = f'@{_after.split("#")[0]}'
                # self.install_name is full spec with @<ref> removed
                self.install_name = full_spec.replace(ver_spec, '')
                self.version_spec = ver_spec
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
            for spec_delim in ('===', '==', '<=', '>=', '!=', '~=', '<', '>', '='):
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
        """The shell command run to install the package as specified"""
        if self.args_str == '':
            args = self.install_name
        else:
            args = self.args_str.replace("<", "'<'").replace(">", "'>'")
        if self.installer == 'pip':
            install_exe = config._pip_executable
            if config.noninteractive:
                args = f'{args} --no-input'
            if config.project is not None:
                install_exe = f'PYTHONUSERBASE="{config.project.project_dir}" {install_exe}'
                args = f'--no-warn-script-location --user {args}'
        else:
            install_exe = self.installer
        return f'{install_exe} install {args}'

    @property
    def is_installed(self):
        """True if the package is installed locally; otherwise, False"""
        installer_kwargs = self.installer_kwargs
        if self.import_name in config._stdlib_modules:
            # smuggled module is part of standard library
            return True
        if (
                installer_kwargs.get('force_reinstall') or
                installer_kwargs.get('ignore_installed') or
                installer_kwargs.get('upgrade')
        ):
            # args that trigger install regardless of existing version
            return False
        if self.args_str == config._smuggled.get(self.cache_key):
            # if the same version of the same package was smuggled from
            # the same source with all the same arguments previously in
            # the current interpreter session/notebook runtime (i.e.,
            # a line is just being rerun with no change)
            return True
        if '/' not in self.install_name:
            # onion comment does not specify a VCS URL
            try:
                installed_version = metadata.version(self.install_name)
            except metadata.PackageNotFoundError:
                # smuggled name could be a non-distribution name from a
                # namespace package (e.g., mpl_toolkits from matplotlib,
                # ipykernel_launcher from ipykernel, pkg_resources from
                # setuptools, etc.) without an accompanying onion
                # comment (so that it was also assigned to
                # self.install_name). importlib.util.find_spec() can
                # locate these if they exist locally.
                module_spec = importlib.util.find_spec(self.import_name)
                if module_spec is None:
                    # requested package is really not installed
                    return False
                if self.import_name in sys.modules:
                    # another edge case to deal with:
                    # importlib.util.find_spec() checks for the package
                    # in sys.modules before checking the file system, so
                    # if the package was previously smuggled/imported,
                    # but the user has since switched to a different
                    # project/environment/pip executable or removed an
                    # entry from sys.path, or the existing version was
                    # loaded from somewhere outside sys.path, then
                    # module_spec will be non-None even though the
                    # package isn't actually available on the current
                    # module search path.
                    if not self.version_spec:
                        # if no specific version was requested and the
                        # module is already available, then it doesn't
                        # matter that it's not currently on sys.path
                        return True
                    return False
                # the requested package is a namespace package
                return True
            except InvalidRequirement:
                # version specifier string isn't valid, but rather than
                # throwing an error here, let pip try to install it and
                # show the user its likely more familiar error message
                return False
            if (
                    not self.version_spec or
                    installed_version in SpecifierSet(self.version_spec)
            ):
                # include explicit `not self.version_spec` condition
                # because `x in SpecifierSet("")` evaluates to False for
                # prerelease versions. If the user has intentionally
                # installed a prerelease version of a package and
                # smuggles it without specifying any particular version
                # constraints, we should allow it
                return True
            return False
        return False

    def _conda_install_package(self):
        raise NotImplementedError(
            "smuggling packages via conda is not yet supported"
        )

    def _pip_install_package(self):
        try:
            stdout = run_shell_command(self.install_cmd)
        except CalledProcessError as e:
            raise InstallerError.from_error(e)
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


def parse_line(line):
    """
    Parse a single line of code, transforming `smuggle` statements.

    Checks a line of user code for a `smuggle` statement and (optional)
    onion comment. If found, replaces them with a corresponding call to
    the `smuggle()` function generated from their parsed contents.

    Parameters
    ----------
    line : str
        A line of Python code.

    Returns
    -------
    str
        The input line, with any `smuggle` statements and onion comments
        replaced with calls to the `smuggle()` function.

    See Also
    --------
    regexps.smuggle_statement_regex :
        Regexp for `smuggle` statements.
    implementations.ipython_pre7.generate_parser_func :
        Generates full parser wrapper function for `IPython<7.0`.
    implementations.ipython_post7.generate_parser_func :
        Generates full parser wrapper function for `IPython<7.0`.

    Notes
    -----
    This function transforms "logical" lines rather than "physical"
    lines. In other words, line continuations and multi-line
    statements/expressions (including `smuggle` statements) should be
    assembled from multiple physical lines before being passed to
    `parse_line()`. This function is wrapped by an implementation-
    specific parser function and called for each (logical) line to be
    parsed.
    """
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
    for n_a in names_aliases:
        if ' as ' in n_a:
            name, alias = n_a.split(' as ')
            name = f'"{qualname_prefix}{name}"'
            alias = f'"{alias.strip()}"'
        else:
            name = f'"{qualname_prefix}{n_a}"'
            alias = f'"{n_a.strip()}"' if is_from_statement else None

        name = name.replace(' ', '')
        smuggle_funcs.append(f'smuggle(name={name}, as_={alias})')

    smuggle_funcs[0] = smuggle_funcs[0][:-1] + kwargs_str + ')'
    return before_chars + '; '.join(smuggle_funcs) + after_chars


def prompt_input(prompt, default=None, interrupt=None):
    """
    Prompt the user for [y]es/[n]o input, return a boolean accordingly.

    Parameters
    ----------
    prompt : str
        The prompt text presented on-screen to the user.
    default : {'y', 'yes', 'n', 'no'}, optional
        The default response if the user presses return without entering
        any text. if `None` (default), re-prompt the user until input is
        provided.
    interrupt : {'y', 'yes', 'n', 'no'}, optional
        The default response if a `KeyboardInterrupt` is raised
        (`CTRL + c` from the command line, "interrupt kernel/runtime"
        from a Jupyter/Colab notebook). If `None` (default), the
        exception is raised. Use with caution to avoid unexpected
        behavior and improperly silencing errors.

    Returns
    -------
    bool
        The boolean value corresponding to the user input (`True` for
        `'y'`/`'yes'`, `False` for `'n'`/`'no'`).

    Notes
    -----
    The `default` value is reflected in the casing of options displayed
    after the `prompt` text (e.g., "`[Y/n]`" if `default="yes"`)
    """
    response_values = {
        'yes': True,
        'y': True,
        'no': False,
        'n': False
    }
    if interrupt is not None:
        interrupt = interrupt.lower()
        if interrupt not in response_values:
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
            raise
        except KeyError:
            pass


def run_shell_command(command, live_stdout=None):
    """
    Execute a shell command and return the generated stdout as a string.

    Parameters
    ----------
    command : str
        The shell command to run. May not end in "*&*", as background
        processes are not supported.
    live_stdout : bool, optional
        Whether to display streaming stdout from `command` execution in
        real time *in addition to* capturing and returning it. If `None`
        (default), behavior is determined by the current value of
        `davos.suppress_stdout`.

    Returns
    -------
    str
        The stdout generated by executing the shell command.

    Raises
    ------
    subprocess.CalledProcessError
        If the command returns a non-zero exit status

    See Also
    --------
    capture_stdout : context manager used when displaying live stdout
    contextlib.redirect_stdout :
        context manager used when not displaying live stdout
    implementations.ipython_common._run_shell_command_helper :
        Helper function to run shell command in IPython environments
    implementations.python._run_shell_command_helper :
        Helper function to run shell command in "pure"
        (non-interactive) Python environments

    Notes
    -----
    `IPython` does not allow shell commands to run background processes.
    `davos` extends this policy to all environments for consistency (and
    lack of reason not to).
    """
    if command.rstrip().endswith('&'):
        raise OSError("Background processes are not supported.")

    if live_stdout is None:
        live_stdout = not config.suppress_stdout
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
        stdout = stdout.getvalue()
    return stdout


def use_project(smuggle_func):
    """
    Use the configured project when smuggling a package.

    Decorator that wraps the `smuggle` function and causes the smuggled
    package to be (installed into, if necessary, and) loaded from the
    package directory for the currently active project, if one is being
    used (i.e., the project given by `davos.project`, if not `None`).

    Parameters
    ----------
    smuggle_func : function
        The `smuggle` function, `davos.core.core.smuggle`.

    Returns
    -------
    function
        The wrapped `smuggle` function.
    """
    @functools.wraps(smuggle_func)
    def smuggle_wrapper(*args, **kwargs):
        project = config.project
        if project is not None:
            # prepend the project's site-packages directory to sys.path
            # so project's package versions are prioritized for import
            # over versions in "regular" environment
            sys.path.insert(0, str(project.site_packages_dir))
            # invalidate sys.meta_path finder caches so the global
            # working set is regenerated based on the updated sys.path.
            # Note: after pretty extensive spot checking, I haven't
            # managed to find a case where this is actually necessary
            # since migrating from pkg_resources to importlib.metadata,
            # but the docs recommend it and the overhead is extremely
            # minor, so probably worth including in case the user or
            # notebook environment has implemented some unusual custom
            # meta path finder
            importlib.invalidate_caches()
            try:
                return smuggle_func(*args, **kwargs)
            finally:
                # after (possibly installing and) loading the package,
                # remove the project's site-packages directory from
                # sys.path and restore the original working set.
                # Note: can't assume the project site-packages dir is
                # still sys.path[0] -- some install options result in
                # other dirs being prepended to load modules installed
                # in custom locations
                sys.path.remove(str(project.site_packages_dir))
                importlib.invalidate_caches()
        else:
            return smuggle_func(*args, **kwargs)

    return smuggle_wrapper


@use_project
def smuggle(
        name,
        as_=None,
        installer='pip',
        args_str='',
        installer_kwargs=None
):
    """
    Load a package into the namespace, installing it first if necessary.

    This implements the core functionality of `davos`. Before user code
    is executed, it is parsed as plain text, and each `smuggle`
    statement (plus, optionally, its corresponding onion comment) is
    replaced with a call to this function. The `smuggle()` function
    first searches for an existing local installation of the specified
    package (that, if applicable, satisfies the version specifier and
    other arguments provided via the onion comment). If one is not
    found, the package is downloaded and installed. The `smuggle()`
    function then loads the package, module, function, or other
    `smuggle`d object into the local namespace as though it were
    `import`ed normally.

    Parameters
    ----------
    name : str
        The qualified name of the package, module, function, or other
        object to be smuggled.
    as_ : str, optional
        The alias under which to load the object into the namespace
        (e.g., "`np`" given the statement "`smuggle numpy as np`").
    installer : {'pip', 'conda'}, optional
        The name of the program used to install the package if a
        satisfactory distribution is not found locally. Defaults to
        `'pip'` if no onion comment is present.
    args_str : str, optional
        Raw arguments to be passed to the `installer` program's
        "install" command. Defaults to an empty string (`''`), if no
        onion comment is present.
    installer_kwargs : dict, optional
        Argument values parsed from `args_str`, supplemented by
        defaults.
    """
    if installer_kwargs is None:
        installer_kwargs = {}

    pkg_name = name.split('.')[0]

    if pkg_name == 'davos':
        raise TheNightIsDarkAndFullOfErrors("Don't do that.")

    onion = Onion(pkg_name, installer=installer,
                  args_str=args_str, **installer_kwargs)

    if onion.is_installed:
        try:
            # Unlike regular import, can be called on non-module items:
            #     ```python
            #     import numpy.array`                   # fails
            #     array = import_item('numpy.array')    # succeeds
            #     ```
            # Also adds module (+ parents, if any) to sys.modules if not
            # already present.
            smuggled_obj = import_name(name)
        except ModuleNotFoundError:
            install_pkg = True
        else:
            install_pkg = False
    else:
        install_pkg = True

    if install_pkg:
        if config.confirm_install and not installer_kwargs.get('no_input'):
            msg = (f"package {pkg_name!r} will be installed with the "
                   f"following command:\n\t`{onion.install_cmd}`\n"
                   f"Proceed?")
            confirmed = prompt_input(msg, default='y')
            if not confirmed:
                raise SmugglerError(
                    f"package {pkg_name!r} not installed"
                ) from None
        installer_stdout = onion.install_package()
        # invalidate sys.meta_path module finder caches. Forces import
        # machinery to notice newly installed module
        importlib.invalidate_caches()
        # if pkg_resources module has already been loaded, reload it in
        # case the just-installed package uses it internally to populate
        # its __version__ attribute from its metadata, Otherwise,
        # pkg_resources's cached working set won't include the new
        # package
        if 'pkg_resources' in sys.modules:
            importlib.reload(sys.modules['pkg_resources'])
        # check whether the smuggled package and/or any
        # installed/updated dependencies were already imported during
        # the current runtime
        prev_imported_pkgs = get_previously_imported_pkgs(installer_stdout,
                                                          onion.installer)
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
            top_level_names_old = []
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
                    # when reloading package below, importlib.reload
                    # doesn't seem to automatically follow and
                    # recursively reload submodules/subpackages loaded
                    # into the top-level module via relative import
                    # (e.g., `from . import submodule`) based on their
                    # *new* locations, if different from their old
                    # locations. So if a previously smuggled package
                    # came from the user's main Python environment, and
                    # the just-smuggled version is now in a project
                    # directory, the old subpackage/submodule object
                    # will be re-used in the new top-level module's
                    # namespace unless we explicitly remove them here
                    # and force their loaders' paths to be recomputed
                    submod_name = mod_name[len(dep_name) + 1:]
                    if submod_name in sys.modules[dep_name].__dict__:
                        top_level_names_old.append(submod_name)
                        del sys.modules[dep_name].__dict__[submod_name]

            # get (but don't pop) top-level package to that it can be
            # reloaded (must exist in sys.modules)
            dep_modules_old[dep_name] = sys.modules[dep_name]
            try:
                importlib.reload(sys.modules[dep_name])
            except (ImportError, RuntimeError):
                # if we aren't able to reload the module, put the old
                # version's submodules we removed back in sys.modules
                # for now, add their names back to the top-level
                # module's __dict__, and prepare to show a warning
                # post-execution.
                # This way:
                #   1. the user still has a working module until they
                #      restart the runtime
                #   2. the error we got doesn't keep getting raised when
                #      we try to reload/import other modules that
                #      import it
                sys.modules.update(dep_modules_old)
                for submod_name in top_level_names_old:
                    sys.modules[dep_name].__dict__[submod_name] = (
                        dep_modules_old[f'{dep_name}.{submod_name}']
                    )
                failed_reloads.append(dep_name)

        if any(failed_reloads):
            # packages with C extensions (e.g., numpy, pandas) cannot be
            # reloaded within an interpreter session. If the package was
            # previously imported (even if not by the user), the kernel
            # will most likely need to be restarted for changes to take
            # effect
            if config.auto_rerun:
                auto_restart_rerun(failed_reloads)
            elif config.noninteractive or installer_kwargs.get('no_input'):
                # if not auto_rerun, only remaining non-interactive
                # option is to raise error
                msg = (
                    "The following packages were previously imported by the "
                    "interpreter and could not be reloaded because their C "
                    "extensions have changed:\n\t"
                    f"[{', '.join(failed_reloads)}]\nRestart the kernel to "
                    "use the newly installed version."
                )
                if config.environment != 'Colaboratory':
                    msg = (
                        f"{msg}\nTo make this happen automatically, set "
                        "'davos.auto_rerun = True'."
                    )
                raise SmugglerError(msg)
            else:
                prompt_restart_rerun_buttons(failed_reloads)
                # if the function above returns, the user has chosen to
                # continue running the notebook rather than restarting
                # to properly reload the package. Issue a warning to let
                # them know to proceed with caution
                if len(failed_reloads) == 1:
                    failed_reloads_str = failed_reloads[0]
                    verb = 'was'
                    failed_ver_string = f'{failed_reloads_str}.__version__'
                else:
                    verb = 'were'
                    failed_ver_string = "These packages' '__version__' attributes"
                    if len(failed_reloads) == 2:
                        failed_reloads_str = " and ".join(failed_reloads)
                    else:
                        failed_reloads_str = (
                            f"{', '.join(failed_reloads[:-1])}, and "
                            f"{failed_reloads[-1]}"
                        )

                msg = (
                    f"{failed_reloads_str} {verb} partially reloaded. "
                    f"{failed_ver_string} may be misleading."
                )
                warnings.warn(msg, RuntimeWarning, stacklevel=3)

        if (
                config._project is None and
                config._pip_executable != config._default_pip_executable
        ):
            # setting `davos.pip_executable` to a non-default value
            # changes the executable used in all cases, but only affects
            # the install location if not using a davos Project
            with handle_alternate_pip_executable(onion.install_name):
                smuggled_obj = import_name(name)
        else:
            smuggled_obj = import_name(name)

    # add the object name/alias to the notebook's global namespace
    if as_ is None:
        # noinspection PyUnboundLocalVariable
        # (false-positive warning, PyCharm doesn't parse logic fully)
        config.ipython_shell.user_ns[name] = smuggled_obj
    else:
        # noinspection PyUnboundLocalVariable
        # (false-positive warning, PyCharm doesn't parse logic fully)
        config.ipython_shell.user_ns[as_] = smuggled_obj
    # cache the smuggled (top-level) package by its full onion comment
    # so rerunning cells is more efficient, but any change to version,
    # source, etc. is caught
    config.smuggled[pkg_name] = onion.cache_key
