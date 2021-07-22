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
    # ADD DOCSTRING
    config.active = True


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
    # ADD DOCSTRING
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
            except:
                # if one assignment fails, no config fields are updated
                for _name, old_value in old_values.items():
                    setattr(config, _name, old_value)
                raise
            else:
                old_values[name] = old_value


def deactivate():
    # ADD DOCSTRING
    config.active = False


def is_active():
    # ADD DOCSTRING
    return config.active


activate()
