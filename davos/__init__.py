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
    'smuggle',
    'use_default_project'
]


import sys
from types import ModuleType

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata

from davos.core.config import DavosConfig


__version__ = metadata.version('davos')

# config must be instantiated before importing implementations module
config = DavosConfig()


import davos.implementations
from davos.core.core import smuggle
from davos.core.exceptions import DavosConfigError
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


sys.modules[__name__].__class__ = ConfigProxyModule

config.active = True

DAVOS_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

use_default_project()
