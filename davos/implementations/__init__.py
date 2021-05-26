# ADD DOCSTRING

# TODO: THIS MODULE SHOULD CONTAIN THE CORRECT IMPLEMENTATION FOR EACH 
#  INTERCHANGEABLE FUNCTION SO THAT OTHER FILES CAN IMPORT FROM HERE


__all__ = ['full_parser']


from davos import config
from davos.core.config import DavosConfig
from davos.core.exceptions import DavosConfigError


import_environment = config.environment

if import_environment == 'Python':
    from davos.implementations.python import (
        _activate_helper, 
        _check_conda_avail_helper,
        _deactivate_helper,
        _run_shell_command_helper,
        generate_parser_func
    )
else:
    from davos.implementations.ipython_common import (
        _check_conda_avail_helper,
        _run_shell_command_helper, 
        _set_custom_showsyntaxerror,
        _showsyntaxerror_davos
    )
    _set_custom_showsyntaxerror()
    if import_environment == 'IPython>=7.0':
        from davos.implementations.ipython_post7 import (
            _activate_helper, 
            _deactivate_helper,
            generate_parser_func
        )
    else:
        from davos.implementations.ipython_pre7 import (
            _activate_helper, 
            _deactivate_helper,
            generate_parser_func
        )
        if import_environment == 'Colaboratory':
            # from davos.implementations.colab import ...
            pass
        else:
            # from davos.implementations.ipython_pre7 import ...
            pass


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
            "Cannot set conda environment. No local conda installation found"
        )
    elif new_env != conf._conda_env:
        if (
                conf._conda_envs_dirs is not None and 
                new_env not in conf._conda_envs_dirs.keys()
        ):
            local_envs = {"', '".join(conf._conda_envs_dirs.keys())}
            raise DavosConfigError(
                "conda_env",
                f"unrecognized environment name: '{new_env}'. Local "
                f"environments are:\n\t{local_envs}"
            )

        conf._conda_env = new_env


def _conda_envs_dirs_fget(conf):
    """getter for davos.config.conda_envs_dirs"""
    if conf._conda_avail is None:
        check_conda()

    return conf._conda_envs_dirs


def _conda_envs_dirs_fset(conf, _):
    """setter for davos.config.conda_envs_dirs"""
    raise DavosConfigError('conda_envs_dirs', 'field is read-only')


DavosConfig.active = property(fget=_active_fget, fset=_active_fset)
DavosConfig.conda_avail = property(fget=_conda_avail_fget, 
                                   fset=_conda_avail_fset)
DavosConfig.conda_env = property(fget=_conda_env_fget, fset=_conda_env_fset)
DavosConfig.conda_envs_dirs = property(fget=_conda_envs_dirs_fget, 
                                       fset=_conda_envs_dirs_fset)
