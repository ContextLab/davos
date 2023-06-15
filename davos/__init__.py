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


__all__ = ['config', 'configure', 'smuggle', 'use_default_project']


import sys
from types import ModuleType

import pkg_resources

from davos.core.config import DavosConfig


__version__ = pkg_resources.get_distribution('davos').version


# config must be instantiated before importing implementations module
config = DavosConfig()


import davos.implementations
from davos.core.core import smuggle
from davos.core.project import DAVOS_PROJECT_DIR, Project, use_default_project


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
        conda_env=...,
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
    conda_env : str, optional
        Value to assign to "`conda_env`" field. Not settable if `conda`
        is not installed (defaults to `None`).
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
    # TODO: perform some value checks upfront to raise relevant errors
    #  before setting some fields and make setting values
    #  order-independent (e.g., noninteractive & confirm_install)
    kwargs = locals()
    old_values = {}
    for name, new_value in kwargs.items():
        if new_value is not Ellipsis:
            old_value = getattr(config, name)
            try:
                setattr(config, name, new_value)
            except Exception:
                # if one assignment fails, no config fields are updated
                for _name, old_value in old_values.items():
                    setattr(config, _name, old_value)
                raise
            old_values[name] = old_value


sys.modules[__name__].__class__ = ConfigProxyModule

config.active = True

DAVOS_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

# TODO: throws error when importing in IPython shell -- add informative
#  error message saying not supported
use_default_project()
