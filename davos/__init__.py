"""
Top-level `davos` module. When imported, the code in this module:

    - initializes the global `davos.config` object
    - enables `davos` functionality in the importing notebook
    - configures the default Project for the session

This module also provides some high-level convenience functions for
managing local Projects and `davos.config` options. Note that at
runtime, this module's object (i.e., "`davos`", given "`import davos`")
will be an instance of the `ConfigProxyModule` class. See that class's
docstring for more info.
"""


__all__ = [
    'DAVOS_CONFIG_DIR',
    'DAVOS_PROJECT_DIR',
    'config',
    'configure',
    'get_project',
    'Project',
    'prune_projects',
    'require_pip',
    'require_python',
    'smuggle',
    'use_default_project'
]


import sys
import warnings
from types import ModuleType

from packaging.specifiers import InvalidSpecifier, SpecifierSet
if sys.version_info < (3, 8):
    import importlib_metadata as metadata
else:
    from importlib import metadata

from davos.core.config import DavosConfig


__version__ = metadata.version('davos')

# config must be instantiated before importing implementations module
config = DavosConfig()


import davos.implementations
from davos.core.core import smuggle
from davos.core.exceptions import DavosConfigError, DavosError
from davos.core.project import (
    DAVOS_CONFIG_DIR,
    DAVOS_PROJECT_DIR,
    get_project,
    Project,
    prune_projects,
    use_default_project
)


class ConfigProxyModule(ModuleType):
    """
    Subclass of Python's built-in `module` type that enables accessing
    `davos.config` fields via the top-level `davos` namespace.

    When imported, the top-level `davos` module object is "converted"
    to an instance of this class (by overwriting its `__class__`
    attribute). The `ConfigProxyModule` class tweaks the built-in
    `module` type's attribute access behavior to:

        1. forward attribute lookups that fail on the module object to
           the `davos.config` object
        2. preferentially forward attribute assignments to the
           `davos.config` object if it defines the given attribute name
        3. support dynamically computed (*and settable*) module-level
           attributes via properties defined by the class.

        This makes it possible to get and set all `davos` configuration
        options directly from the module object itself. For example:
    ```python
    print(davos.config.pip_executable)
    davos.config.project = "myproject"
    ```
    is equivalent to:
    ```python
    print(davos.pip_executable)
    davos.project = "myproject"
    ```
    """

    def __getattr__(self, name):
        try:
            return getattr(config, name)
        except AttributeError:
            raise AttributeError(
                f'module {__name__!r} has no attribute {name!r}'
            ) from None

    def __setattr__(self, name, value):
        if hasattr(config, name):
            setattr(config, name, value)
        else:
            super().__setattr__(name, value)

    @property
    def all_projects(self):
        """
        Get a list of all local projects.

        Returns
        -------
        list of AbstractProject or ConcreteProject
            A list of projects found in `DAVOS_PROJECT_DIR`.
        """
        projects_list = []
        for path in DAVOS_PROJECT_DIR.iterdir():
            if path.is_dir():
                projects_list.append(Project(path.name))
        return projects_list


# pylint: disable=unused-argument
def configure(
        *,
        active=...,
        auto_rerun=...,
        confirm_install=...,
        noninteractive=...,
        pip_executable=...,
        project=...,
        suppress_stdout=...
):
    """
    Set multiple `davos.config` fields at once.

    Parameters
    ----------
    active : bool, optional
        Value to assign to "`active`" field.
    auto_rerun : bool, optional
        Value to assign to "`auto_rerun`" field. Must be `False`
        (default) in Colaboratory notebooks.
    confirm_install : bool, optional
        Value to assign to "`confirm_install`" field.
    noninteractive : bool, optional
        Value to assign to "`noninteractive`" field. Must be `False`
        (default) in Colaboratory notebooks.
    pip_executable : str or pathlib.Path, optional
        Value to assign to "`pip_executable`" field. Must be a path to a
        real file.
    project : str, pathlib.Path, None, or davos.Project, optional
        Value to assign to "`project`" field.
    suppress_stdout : bool, optional
        Value to assign to "`suppress_stdout`" field.

    Raises
    -------
    core.exceptions.ConfigError
        If a config field is assigned an invalid value.

    See Also
    --------
    config.DavosConfig :
        The global `davos` Config object. Offers more detailed
        descriptions of each field.
    """
    kwargs = locals()
    old_values = {}
    # deal with incompatible arguments separately and upfront so that
    # (A) the function fails early rather than having to undo multiple
    # assignments, and (B) the order in which assignments are undone in
    # the event that a *different* assignment fails doesn't cause an
    # incompatibility error.
    # Need to explicitly check if value is True since Ellipsis evaluates
    # to True.
    if kwargs['confirm_install'] is True:
        if kwargs['noninteractive'] is True:
            # passed both `confirm_install=True` and `noninteractive=True`
            raise DavosConfigError(
                'confirm_install',
                "confirm_install=True is incompatible with noninteractive=True"
            )
        if config._noninteractive:
            if kwargs['noninteractive'] is False:
                # if simultaneously disabling non-interactive mode and
                # enabling the confirm_install option (i.e.,
                # `config.noninteractive` is currently `True`,
                # `noninteractive=False` is passed, and
                # `confirm_install=True` is passed), then
                # `config.noninteractive` must be set to `False` before
                # `config.confirm_install` is set to `True`, since both
                # options may not be `True` at the same time. The loop
                # below sets config values based on the `kwargs` dict's
                # insertion order, so simply removing `confirm_install`
                # and re-adding it as the most recent entry ensures that
                # `config.noninteractive` is set first.
                kwargs['confirm_install'] = kwargs.pop('confirm_install')
            else:
                # if `confirm_install=True` is passed,
                # `config.noninteractive` is currently `True`, and
                # `noninteractive=False` is *not* passed, then the
                # resulting values will be incompatible
                raise DavosConfigError(
                    'confirm_install',
                    "field may not be 'True' in noninteractive mode"
                )
    elif (
            kwargs['noninteractive'] is True and
            kwargs['confirm_install'] is False
    ):
        # if simultaneously enabling non-interactive mode and disabling
        # the `confirm_install` option, `config.confirm_install` should
        # be set to `False` before `config.noninteractive` is set to
        # `True` to avoid the spurious warning issued when enabling
        # non-interactive mode when `config.confirm_install` is `True`.
        # Can use the same `dict` insertion order trick as above to
        # ensure this happens.
        kwargs['noninteractive'] = kwargs.pop('noninteractive')

    for name, new_value in kwargs.items():
        if new_value is not Ellipsis:
            old_value = getattr(config, name)
            try:
                setattr(config, name, new_value)
            except Exception:
                # if one assignment fails, no config fields are updated
                for _name, old_value in old_values.items():
                    # bypass checks when resetting fields to save time
                    # and avoid order-dependent issues, since we know
                    # the old values were valid
                    setattr(config, f"_{_name}", old_value)
                raise
            old_values[name] = old_value


def require_pip(version_spec, warn=False, extra_msg=None, prereleases=None):
    """
    Ensure the pip version satisfies a given constraint.

    Specify or constrain the pip version that should be used to install
    smuggled packages in a davos-enhanced notebook. Adding a call to
    this function before smuggling packages in a notebook can be useful
    for communicating to users that installing one or more smuggled
    packages requires a particular pip version (or, more likely, a
    certain minimum version). This function's behavior and arguments are
    analogous to those of davos's `require_python` function. See that
    function's docstring for additional details.

    Parameters
    ----------
    version_spec : str
        A version specifier string in the format described in PEP 440.
        See https://peps.python.org/pep-0440/#version-specifiers. Bare
        version identifiers without a comparison operator are also
        accepted (see the `davos.require_python` function's docstring).
    warn : bool, optional
        If `True`, issue a warning rather than raise an exception if the
        user's pip version doesn't satisfy `version_spec`.
    extra_msg : str, optional
        Additional information to include in the error message.
    prereleases : bool, optional
        Whether to allow prerelease versions. If `None` (default), the
        rule is auto-detected from the version specifier. See
        https://packaging.pypa.io/en/stable/specifiers.html#packaging.specifiers.SpecifierSet

    Examples
    --------
    ```
    import davos

    extra_msg = "pip>=19.0 is needed to install PEP 517-based packages"
    davos.require_pip('>=19.0', extra_msg=extra_msg)
    ```

    See Also
    --------
    require_python :
        Analogous function for constraining the user's Python version.
    """
    valid_specifiers = ('===', '==', '<=', '>=', '!=', '~=', '<', '>')
    for spec in valid_specifiers:
        if version_spec.startswith(spec):
            break
    else:
        if version_spec[0].isdigit():
            version_spec = f'~={version_spec}'
        else:
            raise InvalidSpecifier(
                f"Invalid version specifier: '{version_spec}'"
            )

    version_constraint = SpecifierSet(version_spec, prereleases=prereleases)
    pip_version = metadata.version('pip')
    if pip_version not in version_constraint:
        msg = (
            "The version of pip installed in the environment "
            f"(v{pip_version}) does not satisfy the constraint "
            f"'{version_constraint}'"
        )
        if extra_msg is not None:
            msg = f"{msg}.\n{extra_msg}"

        if warn:
            warnings.warn(msg, category=RuntimeWarning)
        else:
            raise DavosError(msg)


def require_python(version_spec, warn=False, extra_msg=None, prereleases=None):
    """
    Ensure the Python version satisfies a given constraint.

    Specify or constrain the Python version that should be used to run a
    davos-enhanced notebook. Adding a call to this function before
    smuggling packages in a notebook can be useful for communicating to
    users that one or more smuggled packages require a particular Python
    version or range of versions. If the user's Python version
    isn't compatible with `version_spec`, this function will raise an
    error. Additional information can be added to the error message
    via the `extra_msg` argument. A "soft" or suggested constraint can
    be specified by passing `warn=True` to issue a warning rather than
    raise an error.

    `version_spec` may be any valid version specifier defined by PEP
    440 (see https://peps.python.org/pep-0440/#version-specifiers).
    Additionally, passing just a version identifier *without* a
    comparison operator (e.g., "3.9") will be interpreted as a
    "compatible release" specifier. For example,
    `davos.require_python("3.9")` is equivalent to
    `davos.require_python("~=3.9")` and will accept any Python
    patch/macro version in the 3.9 series (i.e., >=3.9.0,<3.10.0).

    Parameters
    ----------
    version_spec : str
        A version specifier string in the format described in PEP 440.
        See https://peps.python.org/pep-0440/#version-specifiers. Bare
        version identifiers without a comparison operator are also
        accepted (see above).
    warn : bool, optional
        If True (default: False), issue a warning rather than raising an
        exception.
    extra_msg : str, optional
        Additional text to include in the error or warning message.
    prereleases : bool, optional
        Whether to allow prerelease versions. If `None` (default), the
        rule is auto-detected from the version specifier. See
        https://packaging.pypa.io/en/stable/specifiers.html#packaging.specifiers.SpecifierSet

    Examples
    --------
    ```
    import davos

    pandas_message = "pandas v1.1.3 supports 3.6.1 and above, 3.7, 3.8, and 3.9"
    davos.require_python(">=3.6.1,<3.10", extra_msg=pandas_message)
    smuggle pandas as pd    # pip: pandas==1.1.3
    ```

    ```
    import davos

    msg = "This notebook replicates analyses originally run with Python 3.9.16"
    davos.require_python("==3.9.16", extra_msg=msg)
    ```

    See Also
    --------
    require_pip :
        Analogous function for constraining the pip version used to
        install missing packages.
    """
    valid_specifiers = ('===', '==', '<=', '>=', '!=', '~=', '<', '>')
    for spec in valid_specifiers:
        if version_spec.startswith(spec):
            break
    else:
        if version_spec[0].isdigit():
            version_spec = f'~={version_spec}'
        else:
            raise InvalidSpecifier(
                f"Invalid version specifier: '{version_spec}'"
            )

    version_constraint = SpecifierSet(version_spec, prereleases=prereleases)
    python_version = sys.version.split()[0]
    if python_version not in version_constraint:
        msg = (
            "The Python version installed in the environment "
            f"(v{python_version}) does not satisfy the constraint "
            f"'{version_constraint}'"
        )
        if extra_msg is not None:
            msg = f"{msg}.\n{extra_msg}"

        if warn:
            warnings.warn(msg, category=RuntimeWarning)
        else:
            raise DavosError(msg)


sys.modules[__name__].__class__ = ConfigProxyModule

config.active = True

DAVOS_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

use_default_project()
