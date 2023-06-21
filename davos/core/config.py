"""
Davos's global configuration object.

The `DavosConfig` class is a singleton whose instance is accessible as
`davos.config`. The config object defines attributes whose values
determine various aspects of the package's behavior. Most of these
attributes can be set by the user to control how, where, and when
smuggled packages are installed. Others are read-only fields that store
information about the notebook environment into which `davos` was
imported and whether or not it supports various `davos` functionality.
The config object's repr displays the current values of all fields, and
multiple fields can be set simultaneously via the `davos.configure()`
function. As of v0.2, `davos.config` fields can also be accessed and set
via attributes of the top-level `davos` module.
"""


__all__ = ['DavosConfig']


import os
import pprint
import shutil
import site
import sys
import sysconfig
import traceback
import warnings
from io import StringIO
from os.path import expandvars
from pathlib import Path

from davos.core.exceptions import (
    DavosConfigError,
    DavosError,
    ProjectNotebookNotFoundError
)


class SingletonConfig(type):
    """Metaclass that enforces singleton behavior for `DavosConfig`"""

    __instance = None

    def __call__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__call__(*args, **kwargs)
        return cls.__instance


class DavosConfig(metaclass=SingletonConfig):
    """
    The global `davos` config object.

    Defines the following fields:

        **Configurable fields**:
            active : bool
                Whether the `davos` parser should be run on subsequent
                input (cells, in Jupyter/Colab notebooks, lines in pure
                Python; default: `True`)
            auto_rerun : bool
                If `True` (default: `False`), automatically restart the
                interpreter session and rerun previously executed code
                upon smuggling a package that cannot be dynamically
                reloaded (Note: currently implemented for Jupyter
                notebooks only)
            conda_env: str or None
                NOTE: NOT CURRENTLY SUPPORTED.
                The name of the resident conda environment of the
                current Python interpreter, if running within a `conda`
                environment. Otherwise, `None`.
            confirm_install : bool
                If `True` (default: `False`), prompt for user input
                before installing any smuggled packages not already
                available locally.
            noninteractive : bool
                If `True` (default: `False`) run `davos` in
                non-interactive mode. All user input and confirmation
                will be disabled. **Note**: In Jupyter environments, the
                value of `auto_rerun` will determine whether `davos`
                restarts the kernel or throws an error when a smuggled
                package cannot be dynamically reloaded.
            pip_executable : str of pathlib.Path
                The path to the `pip` executable that should be used.
                Must be a path to a real file. Defaults to automatically
                discovered executable, if available.
            project : davos.core.project.ConcreteProject
                The "Project" environment into which smuggled packages
                should be installed. The default is a notebook-specific
                Project whose name is the path to the current notebook.
                This field may also be specified as a `str` or
                `pathlib.Path`, which will be converted to a
                `ConcreteProject` instance on assignment. If set to
                `None`, smuggled packages will be installed into the
                regular Python environment rather than isolated in a
                Project. Projects are a virtual environment-like
                construct specific to `davos`. For additional info, see
                https://github.com/ContextLab/davos#readme and
                the `davos.core.project` module.
            suppress_stdout: bool
                If `True` (default: `False`), suppress all unnecessary
                output issued by the program. This is often useful when
                smuggling packages that need to install many
                dependencies and therefore generate extensive output.
        **Read-only fields**:
            conda_avail : bool
                NOTE: NOT CURRENTLY SUPPORTED.
                Whether or not `conda` is installed and the `conda`
                executable is accessible from the Python interpreter
            conda_envs_dirs : dict or None
                NOTE: NOT CURRENTLY SUPPORTED.
                If `conda_avail` is `True`, a mapping of conda
                environment names to their environment directories.
                Otherwise, `None`.
            environment : {'Python', 'IPython<7.0', 'IPython>=7.0',
                          'Colaboratory'}
                The environment in which `davos` is running. Determines
                which interchangeable implementation functions are used,
                whether certain config fields are writable, and various
                other behaviors.
            ipython_shell : IPython.core.interactiveshell.InteractiveShell
                The global `IPython` interactive shell instance.
            smuggled : dict
                A cache of packages previously smuggled during the
                current interpreter session, implemented as a dict whose
                keys are package names and whose values are the
                arguments supplied via the corresponding Onion comment.
                The cache is implemented as such so that altering any
                arguments passed to the installer will prompt a
                re-installation.
    """

    # noinspection PyUnusedLocal
    # pylint: disable=unused-argument, missing-function-docstring
    @staticmethod
    def __mock_sorted(__iterable, key=None, reverse=False):
        """
        Mock for built-in `sorted` that returns unsorted iterable.

        Used to temporarily monkeypatch built-in `sorted` function in
        `pprint` module when formatting display for `self.__repr__`
        method. `dict` items in `smuggled` field should be shown in
        insertion order, not alphabetically, because they represent a
        history of cached `smuggle` commands. However,
        `pprint.PrettyPrinter` didn't provide the option to *not* sort
        `dict`s until Python 3.8, so for earlier versions, this is
        assigned to `pprint.sorted` so that it takes priority over the
        built-in `sorted` in module's namespace lookup chain.

        Parameters
        ----------
        __iterable : iterable
            The iterable to be "sorted."
        key : callable, optional
            Has no effect; exists to make function signature match that
            of built-in `sorted` function.
        reverse : bool
            Has no effect; exists to make function signature match that
            of built-in `sorted` function.

        Returns
        -------
        iterable
            The object passed as `__iterable`, unaltered.
        """
        return __iterable

    def __init__(self):
        ########################################
        #           READ-ONLY FIELDS           #
        ########################################
        try:
            # (function exists globally when imported into IPython context)
            self._ipython_shell = get_ipython()
        except NameError:
            # see _block_greedy_ipython_completer() docstring
            _block_greedy_ipython_completer()
            # imported from a non-interactive Python script
            self._ipython_shell = None
            self._environment = 'Python'
        else:
            import IPython
            if isinstance(
                    self._ipython_shell,
                    IPython.terminal.interactiveshell.TerminalInteractiveShell
            ):
                _msg = ("davos does not officially support IPython terminal "
                        "shells. Some features may not work as expected.")
                warnings.warn(_msg, category=RuntimeWarning)
            if IPython.version_info[0] >= 7:
                if 'google.colab' in str(self._ipython_shell):
                    self._environment = 'Colaboratory'
                else:
                    self._environment = 'IPython>=7.0'
            else:
                self._environment = 'IPython<7.0'
        self._conda_avail = None
        self._conda_envs_dirs = None
        self._default_pip_executable = self._find_default_pip_executable()
        self._ipy_showsyntaxerror_orig = None
        self._repr_formatter = pprint.PrettyPrinter()
        if sys.version_info.minor >= 8:
            # sort_dicts constructor param added in Python 3.8, defaults
            # to True. Set it to False here for consistency.
            self._repr_formatter._sort_dicts = False
        self._smuggled = {}
        self._stdlib_modules = _get_stdlib_modules()
        ########################################
        #          CONFIGURABLE FIELDS         #
        ########################################
        self._active = True
        self._auto_rerun = False
        self._conda_env = None
        self._confirm_install = False
        self._noninteractive = False
        self._project = None
        self._suppress_stdout = False
        self._pip_executable = self._default_pip_executable

    def __repr__(self):
        cls_name = self.__class__.__name__
        base_indent = len(cls_name) + 1
        attrs_in_repr = ['active', 'auto_rerun']
        if self._conda_avail is not None:
            attrs_in_repr.append('conda_avail')
            if self._conda_avail is True:
                attrs_in_repr.extend(['conda_env', 'conda_envs_dirs'])
        attrs_in_repr.extend([
            'confirm_install',
            'environment',
            'ipython_shell',
            'noninteractive',
            'pip_executable',
            'project',
            'suppress_stdout',
            'smuggled'
        ])
        newline_delim = ',\n' + ' ' * base_indent
        last_item_ix = len(attrs_in_repr) - 1
        stream = StringIO()
        stream.write(f'{cls_name}(')
        try:
            if sys.version_info.minor < 8:
                # monkeypatch built-in sorted function in pprint module
                # while formatting __repr__ output
                pprint.sorted = self.__mock_sorted
            for i, attr_name in enumerate(attrs_in_repr):
                attr_indent = base_indent + len(attr_name) + 1
                is_last = i == last_item_ix
                stream.write(f'{attr_name}=')
                self._repr_formatter._format(getattr(self, f'_{attr_name}'),
                                             stream=stream,
                                             indent=attr_indent,
                                             allowance=int(not is_last),
                                             context={},
                                             level=0)
                if not is_last:
                    stream.write(newline_delim)
        finally:
            if sys.version_info.minor < 8:
                try:
                    # delete the patch function so it doesn't interfere
                    # with other libraries using pprint module
                    # noinspection PyUnresolvedReferences
                    del pprint.sorted
                except AttributeError:
                    pass
        repr_ = stream.getvalue()
        stream.close()
        return repr_ + ')'

    @property
    def auto_rerun(self):
        return self._auto_rerun

    @auto_rerun.setter
    def auto_rerun(self, value):
        if not isinstance(value, bool):
            raise DavosConfigError('auto_rerun',
                                   "field may be 'True' or 'False'")
        if self._environment == 'Colaboratory':
            raise DavosConfigError(
                'auto_rerun',
                'automatic rerunning of cells not available in Colaboratory'
            )
        self._auto_rerun = value

    @property
    def confirm_install(self):
        return self._confirm_install

    @confirm_install.setter
    def confirm_install(self, value):
        if not isinstance(value, bool):
            raise DavosConfigError('confirm_install',
                                   "field may be 'True' or 'False'")
        if self._noninteractive and value:
            raise DavosConfigError('confirm_install',
                                   "field may not be 'True' in noninteractive "
                                   "mode")
        self._confirm_install = value

    @property
    def environment(self):
        return self._environment

    @environment.setter
    def environment(self, _):
        raise DavosConfigError('environment', 'field is read-only')

    @property
    def ipython_shell(self):
        return self._ipython_shell

    @ipython_shell.setter
    def ipython_shell(self, _):
        raise DavosConfigError('ipython_shell', 'field is read-only')

    @property
    def noninteractive(self):
        return self._noninteractive

    @noninteractive.setter
    def noninteractive(self, value):
        if not isinstance(value, bool):
            raise DavosConfigError('noninteractive',
                                   "field may be 'True' or 'False'")
        if self._environment == 'Colaboratory':
            raise DavosConfigError(
                'noninteractive',
                "noninteractive mode not available in Colaboratory"
            )
        if value and self._confirm_install:
            warnings.warn(
                "noninteractive mode enabled, setting `confirm_install = False`"
            )
            self._confirm_install = False
        self._noninteractive = value

    @property
    def pip_executable(self) -> str:
        return self._pip_executable

    @pip_executable.setter
    def pip_executable(self, exe_path):
        try:
            exe_path = Path(expandvars(exe_path)).expanduser().resolve(strict=True)
        except FileNotFoundError as e:
            raise DavosConfigError(
                'pip_executable',  f"No such file or directory: '{exe_path}'"
            ) from e
        if str(exe_path) != self._pip_executable:
            if not exe_path.is_file():
                raise DavosConfigError(
                    'pip_executable', f"'{exe_path}' is not an executable file"
                )
            self._pip_executable = str(exe_path)

    @property
    def project(self):
        return self._project

    @project.setter
    def project(self, proj):
        from davos.core.project import AbstractProject, ConcreteProject, Project
        if proj is None or isinstance(proj, ConcreteProject):
            self._project = proj
        elif isinstance(proj, AbstractProject):
            raise ProjectNotebookNotFoundError(
                "The notebook associated with this Project does not exist: "
                f"{proj.name!r}. If the notebook has been moved or renamed, "
                "you can point the Project to its new location with:\n\t"
                "`<project>.rename('<new_notebook_path>')`\n or remove the "
                "project fully with:\n\t`<project>.remove()`"
            )
        elif isinstance(proj, (str, Path)):
            proj = Project(proj)
            if isinstance(proj, AbstractProject):
                raise ProjectNotebookNotFoundError(
                    "To use a project associated with a specific notebook, "
                    "the specified path must point to an existing Jupyter "
                    f"notebook ('.ipynb') file. {proj.name!r} could not be "
                    f"found)."
                )
            self._project = proj
        else:
            raise DavosConfigError(
                'project',
                "the project may be set using a str, pathlib.Path, "
                "davos.Project instance, or None"
            )

    @property
    def smuggled(self):
        return self._smuggled

    @smuggled.setter
    def smuggled(self, _):
        raise DavosConfigError('smuggled', 'field is read-only')

    @property
    def suppress_stdout(self):
        return self._suppress_stdout

    @suppress_stdout.setter
    def suppress_stdout(self, value):
        if not isinstance(value, bool):
            raise DavosConfigError('suppress_stdout',
                                   "field may be 'True' or 'False'")
        self._suppress_stdout = value

    def _find_default_pip_executable(self):
        """
        Finds the pip executable that should be used to install smuggled
        packages that don't exist locally and returns its path.

        If the notebook kernel lives inside some sort of virtual
        environment, running `pip install <pkg>` in a subshell would
        install <pkg> in the wrong place (see ContextLab/davos#10), so
        shell commands used to install smuggled packages need to
        reference the pip executable by its full path.

        Can pretty safely assume pip is installed -- been included with
        all Python binary installers since v3.4. Could include a bunch
        of additional fallback checks here if we can't find the
        executable (check f'{site.getuserbase()}/bin/pip', see if pip
        module is importable, fall back to f'{sys.executable} -m pip',
        etc.) but not worth the extra complexity since this is
        sufficient in nearly all cases... and in those where it's not,
        the user has manually altered their environment in some way and
        we *should* throw an error.

        Returns
        -------
        str
            absolute path to the default pip executable
        """
        if self._environment == 'Colaboratory':
            # Colab currently has a custom `pip` executable installed in
            # a non-standard location, so check that (hard-coded) first,
            # but still check the other locations after in case they
            # ever update it.
            expected_pip_exe_colab = '/usr/local/bin/pip'
            if Path(expected_pip_exe_colab).is_file():
                return expected_pip_exe_colab
        # possible locations for pip executable in standard setups.
        # These are based on how pip internally locates its executable
        # in order to uninstall itself, plus a few additional
        # possibilities to handle edge cases. See:
        #   - https://github.com/pypa/pip/pull/10358
        #   - https://discuss.python.org/t/proper-way-to-determine-install-location-of-console-scripts/7188
        #   - https://github.com/pypa/pip/blob/3fe826c/src/pip/_internal/locations.py#L63-L91
        #   - https://github.com/pypa/pip/blob/7ff4da6/src/pip/_internal/locations/__init__.py
        locations_to_check = [
            # normal install, newer pip versions
            Path(sysconfig.get_path('scripts'), 'pip'),
            # normal install, older pip versions
            Path(sys.prefix, 'bin', 'pip'),
            Path(sys.exec_prefix, 'bin', 'pip'),
            # prefixes can be configured when building the interpreter,
            # so also try checking another way on the off chance the
            # user has an unusual/custom Python build
            Path(sys.executable).with_name('pip'),
            # check possible locations for user-level installation only
            # if a "normal" interpreter-specific installation isn't
            # found, since user install is non-default and generally a
            # fallback solution for when user doesn't have access to the
            # part of the filesystem where the interpreter lives
            # user install, newer pip versions
            Path(sysconfig.get_path('scripts', f'{os.name}_user'), 'pip'),
            # user install, older pip versions
            Path(site.getuserbase(), 'bin', 'pip'),
            # some linux distros patch console script locations in weird
            # ways...
            Path(site.getusersitepackages(), 'bin', 'pip')
            # ^note: in many cases, some of these will be duplicates
        ]
        for location in locations_to_check:
            if location.is_file():
                return str(location)
        if self._environment == 'Colaboratory':
            # Can also fall back to checking $PATH in Colab, but can't
            # assume this for a regular Jupyter notebook -- if the
            # kernel is running in a virtual environment, this would
            # give us the pip executable for the notebook server
            # environment instead
            pip_exe = shutil.which('pip')
            if pip_exe is not None:
                return pip_exe
        raise DavosError(
            "Could not locate a 'pip' executable in the current Python "
            "environment. To ensure you have 'pip' installed in your "
            "environment (and install it, if not), run\n\t"
            f"`{sys.executable} -m ensurepip`"
        )


def _block_greedy_ipython_completer():
    """
    Prevent `IPython` autocomplete from preemptively importing `davos`.

    `IPython` uses "greedy" TAB-completion, meaning that in some cases,
    it will proactivly execute code in order to provide autocomplete
    suggestions. For instance, if the user presses the TAB key while
    typing an `import` statement, `IPython` will actually import the
    module internally to generate suggestions from the names available
    in its namespace. And because Python caches the module in
    `sys.modules` during this initial "hidden" `import`, any top-level
    (initialization) code it contains is skipped for all subsequent
    imports.

    This is particularly problematic for packages that set
    `IPython`- or notebook-specific options or behavors on import (like
    `davos`) because the autocomplete mechanism imports them *outside*
    the `IPython` environment. To prevent this, `davos` parses the stack
    trace for any calls originating from IPython's autocomple module
    (`IPython.core.completerlib`) and, if any are found, removes
    the relevant `davos` modules from `sys.modules` so they're reloaded
    when *actually* imported from the notebook. It then raises a generic
    exception that triggers the autocomple process to exit.

    See Also
    --------
    IPython.core.completerlib.try_import :
        runs import statements to generate autocomplete suggestions

    Notes
    -----
    `IPython`'s greedy completion behavior is enabled by default and can
    be disabled by running the following "magic" commands:
    ```python
    %config IPCompleter.greedy = False
    %config IPCompleter.use_jedi = False
    ```
    or the setting the following options in the `IPython` config
    file:
    ```python
    c.IPCompleter.greedy = False
    c.IPCompleter.use_jedi = False
    ```
    """
    # extract 20 most recent entries. Completer module usually appears
    # ~12 entries deep, after davos & importlib, so add small buffer to
    # be safe and start searching from oldest.
    stack_trace = traceback.extract_stack(limit=20)
    # drop most recent 3 frames, which will always be internal davos
    # calls due to package layout
    for frame in stack_trace[:-3]:
        if frame.filename.endswith('IPython/core/completerlib.py'):
            # if stack contains calls to functions in completer module,
            # remove davos.core & davos.core.config from sys.modules so
            # they're reloaded when imported for real and raise generic
            # exception to make completer function return early.
            del sys.modules['davos.core']
            del sys.modules['davos.core.config']
            # pylint: disable=broad-exception-raised
            raise Exception


def _get_stdlib_modules():
    """
    Get names of standard library modules.

    For efficiency, get standard library module names upfront. This
    allows us to skip file system checks for any smuggled stdlib
    modules.

    Returns
    -------
    frozenset of str
        The names of standard library modules for the user's Python
        implementation.
    """
    if sys.version_info.minor >= 10:
        return sys.stdlib_module_names

    stdlib_dir = Path(os.__file__).parent
    stdlib_modules = []
    for p in stdlib_dir.iterdir():
        if (
                (p.is_dir() and p.joinpath('__init__.py').is_file()) or
                p.suffix == '.py'
        ):
            stdlib_modules.append(p.stem)

    builtins_dir = stdlib_dir.joinpath('lib-dynload')
    if builtins_dir.is_dir():
        for p in builtins_dir.glob('*.cpython*.so'):
            stdlib_modules.append(p.stem.split('.')[0])

    stdlib_modules.extend(sys.builtin_module_names)
    return frozenset(stdlib_modules)
