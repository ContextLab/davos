"""
Top-level `davos` module. Initializes the global `davos` config object
and defines some convenience functions for accessing/setting
`davos.config` values.
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
# TODO: refactor to find a cleaner way of setting this during __init__,
#  also possibly defer lazily? Or if run at import, maybe async?
from davos.core.project import DAVOS_PROJECT_DIR, Project, use_default_project


class ConfigProxyModule(ModuleType):
    """TODO: add docstring"""
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
        """TODO: add docstring"""
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
