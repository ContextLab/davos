"""
This module dynamically imports and defines functions based on the
environment into which `davos` is imported.

Some `davos` functionality requires (often quite drastically) different
implementations depending on certain properties of the importing
environment (e.g., "regular" Python vs IPython, the IPython notebook
front-end, etc.). To deal with this, environment-dependent parts of core
features and behaviors (in the `davos.core` subpackage) are isolated and
abstracted as "helper functions". Multiple, interchangeable
implementations of each helper function are organized into
per-environment modules within the `davos.implementations` subpackage.
At runtime, this module selectively imports a single version of each
helper function based on the global Python environment. `davos.core`
modules can then access the correct implementation of each helper
function regardless of the environment by importing it from the
top-level `davos.implementations` module. This also allows individual
`davos.implementations` modules to import packages that aren't
guaranteed to be installed outside certain environments (e.g., `google`,
`ipykernel`) without requiring them as dependencies of the overall
`davos` package.

The importing environment is determined by the value of the
`environment` field of the global `DavosConfig` instance, so it's
important that:
    1. the global `davos.config` object is instantiated before this
       module is imported
    2. the top-level namespace of `davos.core.config` does not import
       this module or any others that do so, recursively.
    3. any modules imported by this module that in turn rely on
       implementation-specific functions are loaded *after* those
       functions are defined, here.
"""


__all__ = [
    'auto_restart_rerun',
    'full_parser',
    'generate_parser_func',
    'prompt_restart_rerun_buttons'
]


from davos import config
from davos.core.config import DavosConfig
from davos.core.exceptions import DavosConfigError


import_environment = config.environment


if import_environment == 'Python':
    # noinspection PyUnresolvedReferences
    from davos.implementations.python import (
        _activate_helper,
        _check_conda_avail_helper,
        _deactivate_helper,
        _run_shell_command_helper,
        auto_restart_rerun,
        generate_parser_func,
        prompt_restart_rerun_buttons
    )
else:
    # noinspection PyUnresolvedReferences
    from davos.implementations.ipython_common import (
        _check_conda_avail_helper,
        _run_shell_command_helper,
        _set_custom_showsyntaxerror
    )

    _set_custom_showsyntaxerror()

    if import_environment == 'IPython>=7.0':
        from davos.implementations.ipython_post7 import (
            _activate_helper,
            _deactivate_helper,
            generate_parser_func
        )
        from davos.implementations.jupyter import (
            auto_restart_rerun,
            prompt_restart_rerun_buttons
        )
    else:
        from davos.implementations.ipython_pre7 import (
            _activate_helper,
            _deactivate_helper,
            generate_parser_func
        )
        if import_environment == 'Colaboratory':
            from davos.implementations.colab import (
                auto_restart_rerun,
                prompt_restart_rerun_buttons
            )
        else:
            from davos.implementations.jupyter import (
                auto_restart_rerun,
                prompt_restart_rerun_buttons
            )

from davos.core.core import check_conda, smuggle, parse_line


# Implementation-specific wrapper around davos.core.core.parse_line
full_parser = generate_parser_func(parse_line)


########################################
#  ADDITIONAL DAVOS.CONFIG PROPERTIES  #
########################################
# some properties are added to the davos.core.config.DavosConfig class
# here rather than when it's initially defined, because they depend on
# either:
#  1. an implementation-specific function that hasn't been determined
#     yet, or
#  2. a function defined in the `davos.core.core` module (namely,
#     `check_conda`) which needs to be imported after
#     implementation-specific functions are set here.


# pylint: disable=unused-argument
# noinspection PyUnusedLocal
def _active_fget(conf):
    """getter for davos.config.active"""
    return config._active


def _active_fset(conf, value):
    """setter for davos.config.active"""
    if value is True:
        _activate_helper(smuggle, full_parser)
    elif value is False:
        _deactivate_helper(smuggle, full_parser)
    else:
        raise DavosConfigError('active', "field may be 'True' or 'False'")

    conf._active = value


def _conda_avail_fget(conf):
    """getter for davos.config.conda_avail"""
    if conf._conda_avail is None:
        check_conda()

    return conf._conda_avail


# noinspection PyUnusedLocal
def _conda_avail_fset(conf, _):
    """setter for davos.config.conda_avail"""
    raise DavosConfigError('conda_avail', 'field is read-only')


def _conda_env_fget(conf):
    """getter for davos.config.conda_env"""
    if conf._conda_avail is None:
        # _conda_env is None if we haven't checked conda yet *and* if
        # conda is not available vs _conda_avail is None only if we
        # haven't checked yet
        check_conda()

    return conf._conda_env


def _conda_env_fset(conf, new_env):
    """setter for davos.config.conda_env"""
    if conf._conda_avail is None:
        check_conda()

    if conf._conda_avail is False:
        raise DavosConfigError(
            "conda_env",
            "cannot set conda environment. No local conda installation found"
        )
    if new_env != conf._conda_env:
        if (
                conf._conda_envs_dirs is not None and
                new_env not in conf._conda_envs_dirs.keys()
        ):
            local_envs = {"', '".join(conf._conda_envs_dirs.keys())}
            raise DavosConfigError(
                "conda_env",
                f"unrecognized environment name: '{new_env}'. Local "
                f"environments are:\n\t'{local_envs}'"
            )

        conf._conda_env = new_env


def _conda_envs_dirs_fget(conf):
    """getter for davos.config.conda_envs_dirs"""
    if conf._conda_avail is None:
        check_conda()

    return conf._conda_envs_dirs


# noinspection PyUnusedLocal
def _conda_envs_dirs_fset(conf, _):
    """setter for davos.config.conda_envs_dirs"""
    raise DavosConfigError('conda_envs_dirs', 'field is read-only')


DavosConfig.active = property(fget=_active_fget, fset=_active_fset)

DavosConfig.conda_avail = property(fget=_conda_avail_fget,
                                   fset=_conda_avail_fset)

DavosConfig.conda_env = property(fget=_conda_env_fget, fset=_conda_env_fset)

DavosConfig.conda_envs_dirs = property(fget=_conda_envs_dirs_fget,
                                       fset=_conda_envs_dirs_fset)
