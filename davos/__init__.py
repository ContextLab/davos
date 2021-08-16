"""
Top-level `davos` module. Initializes the global `davos` config object
and defines some convenience functions for accessing/setting
`davos.config` values.
"""


import pkg_resources
from davos.core.config import DavosConfig


__all__ = [
    'activate',
    'config',
    'configure',
    'deactivate',
    'is_active',
    'smuggle'
]

__version__ = pkg_resources.get_distribution('davos').version


# config must be instantiated before importing implementations module
config = DavosConfig()


import davos.implementations
from davos.core.core import smuggle


def activate():
    """
    Activate the `davos` parser if it is not currently active.

    Convenience function equivalent to running
    `davos.config.active = True`. Enables the `davos` parser and injects
    the `smuggle()` function into the namespace.
    """
    config.active = True


# pylint: disable=unused-argument
def configure(
        *,
        active=...,
        auto_rerun=...,
        conda_env=...,
        confirm_install=...,
        noninteractive=...,
        pip_executable=...,
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
    pip_executable : str or pathlib.Path
        Value to assign to "`pip_executable`" field. Must be a path to a
        real file.
    suppress_stdout : bool
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
            else:
                old_values[name] = old_value


def deactivate():
    """
    Deactivate the `davos` parser if it is currently active.

    Convenience function equivalent to running
    `davos.config.active = False`. Disables the `davos` parser and
    deletes the name `smuggle` from the namespace if and only if it
    refers to the `smuggle()` function.
    """
    config.active = False


def is_active():
    """
    Check whether the `davos` parser currently active.

    Convenience function that simply returns the value of
    `davos.config.active`.

    Returns
    -------
    bool
        Whether or not the `davos` parser is currently active.

    """
    return config.active


activate()
