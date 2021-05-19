# ADD DOCSTRING

# TODO: THIS MODULE SHOULD CONTAIN THE CORRECT IMPLEMENTATION FOR EACH 
#  INTERCHANGEABLE FUNCTION SO THAT OTHER FILES CAN IMPORT FROM HERE

# TODO: add __all__


from davos import config
from davos.core.config import DavosConfig
from davos.core.exceptions import DavosConfigError


import_environment = config.environment

if import_environment == 'Python':
    from davos.implementations.python import (
        _activate_helper, 
        _check_conda_avail_helper,
        _deactivate_helper,
        _run_shell_command_helper
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
            _deactivate_helper
        )
    else:
        from davos.implementations.ipython_pre7 import (
            _activate_helper, 
            _deactivate_helper
        )
        if import_environment == 'Colaboratory':
            # from davos.implementations.colab import ...
            pass
        else:
            # from davos.implementations.ipython_pre7 import ...
            pass


from davos.core.core import check_conda, smuggle, smuggle_parser


def _active_fget(conf):
    """getter for davos.config.active"""
    return config._active


def _active_fset(conf, value):
    """setter for davos.config.active"""
    if value is True:
        _activate_helper(smuggle, smuggle_parser)
    elif value is False:
        _deactivate_helper(smuggle, smuggle_parser)
    else:
        raise DavosConfigError('active', "field may be 'True' or 'False'")

    conf._active = value


def _conda_avail_fget(conf):
    if conf._conda_avail is None:
        check_conda()

    return conf._conda_avail


def _conda_avail_fset(conf, _):
    raise DavosConfigError('conda_avail', 'field is read-only')


def _conda_env_fget(conf):
    if conf._conda_avail is None:
        # _conda_env is None if we haven't checked conda yet *and* if 
        # conda is not available vs _conda_avail is None only if we 
        # haven't checked yet
        check_conda()

    return conf._conda_env


def _conda_env_fset(conf, new_env):
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
    if conf._conda_avail is None:
        check_conda()

    return conf._conda_envs_dirs


def _conda_envs_dirs_fset(conf, _):
    raise DavosConfigError('conda_envs_dirs', 'field is read-only')


DavosConfig.active = property(fget=_active_fget, fset=_active_fset)
DavosConfig.conda_avail = property(fget=_conda_avail_fget, fset=_conda_avail_fset)
DavosConfig.conda_env = property(fget=_conda_env_fget, fset=_conda_env_fset)
DavosConfig.conda_envs_dirs = property(fget=_conda_envs_dirs_fget, fset=_conda_envs_dirs_fset)
