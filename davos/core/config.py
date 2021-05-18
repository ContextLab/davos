# ADD DOCSTRING


__all__ = ['DavosConfig']


import pathlib
import sys
import warnings
from os.path import expandvars

from davos.core.exceptions import DavosConfigError


class SingletonConfig(type):
    __instance = None
    def __call__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__call__(*args, **kwargs)
        return cls.__instance


class DavosConfig(metaclass=SingletonConfig):
    @staticmethod
    def _get_stdlib_modules():
        stdlib_dir = pathlib.Path(pathlib.__file__).parent
        stdlib_modules = set(p.stem for p in stdlib_dir.iterdir())
        try:
            stdlib_modules.remove('site-packages')
        except KeyError:
            pass
        if sys.platform.startswith('linux'):
            try:
                stdlib_modules.remove('dist-packages')
            except KeyError:
                pass
        return stdlib_modules

    # noinspection PyFinal
    # suppressing due to PyCharm bug where inspection doesn't 
    # differentiate between declarations here and in stub file (which it 
    # should, according to PEP 591)
    def __init__(self):
        ########################################
        #           READ-ONLY FIELDS           #
        ########################################
        try:
            # noinspection PyUnresolvedReferences
            self._ipython_shell = get_ipython()
        except NameError:
            # imported from a non-interactive Python script
            self._ipython_shell = None
            self._environment = 'Python'
        else:
            import IPython
            if IPython.version_info[0] < 7:
                if 'google.colab' in str(self._ipython_shell):
                    self._environment = 'Colaboratory'
                else:
                    self._environment = 'IPython<7.0'
            else:
                self._environment = 'IPython>=7.0'
        self._conda_avail = None
        self._conda_envs_dirs = None
        self._ipy_showsyntaxerror_orig = None
        self._smuggled = {}
        self._stdlib_modules = self._get_stdlib_modules()
        ########################################
        #          CONFIGURABLE FIELDS         #
        ########################################
        self._active = True
        self._allow_rerun = False
        self._conda_env = None
        self._confirm_install = False
        self._noninteractive = False
        self._suppress_stdout = False
        # re: see ContextLab/davos#10
        # reference pip executable using full path so IPython shell 
        # commands install packages in the notebook kernel environment, 
        # not the notebook server environment
        #
        # pip is assumed to be installed -- been included by default 
        # with Python binary installers since 3.4
        self._pip_executable = f'{sys.exec_prefix}/bin/pip'

    def __repr__(self):
        # TODO: implement me 
        #  also implement _repr_html_ and/or _repr_pretty_ et al.
        return super().__repr__()
        
    @property
    def active(self):
        return self._active
    
    @active.setter
    def active(self, state):
        if state is True:
            from davos.implementations import activate as switch
        elif state is False:
            from davos.implementations import deactivate as switch
        else:
            raise DavosConfigError('active', "field may be 'True' or 'False'")
        switch()
        
    @property
    def allow_rerun(self):
        return self._allow_rerun
    
    @allow_rerun.setter
    def allow_rerun(self, value):
        if not isinstance(value, bool):
            raise DavosConfigError('allow_rerun', 
                                   "field may be 'True' or 'False'")
        self._allow_rerun = value
        
    @property
    def conda_avail(self):
        if self._conda_avail is None:
            from davos.implementations import check_conda
            check_conda()
        return self._conda_avail
            
    @conda_avail.setter
    def conda_avail(self, _):
        raise DavosConfigError('conda_avail', 'field is read-only')
    
    @property
    def conda_env(self):
        if self._conda_avail is None:
            # _conda_env is None if we haven't checked conda 
            # yet *and* if conda is not available vs _conda_avail is 
            # None only if we haven't checked yet
            from davos.implementations import check_conda
            check_conda()
        return self._conda_env
    
    @conda_env.setter
    def conda_env(self, new_env):
        if self._conda_avail is None:
            from davos.implementations import check_conda
            check_conda()
        if self._conda_avail is False:
            raise DavosConfigError(
                "conda_env", 
                "Cannot set conda environment. No local conda installation found"
            )
        elif new_env != self._conda_env:
            if (
                    self._conda_envs_dirs is not None and 
                    new_env not in self._conda_envs_dirs.keys()
            ): 
                raise DavosConfigError(
                    "conda_env", 
                    f"unrecognized environment name: '{new_env}'. Local "
                    f"environments are:\n\t{', '.join(self._conda_envs_dirs.keys())}"
                )
            self._conda_env = new_env
                
    @property
    def conda_envs_dirs(self):
        if self._conda_avail is None:
            from davos.implementations import check_conda
            check_conda()
        return self._conda_envs_dirs
        
    @property
    def confirm_install(self):
        return self._confirm_install
    
    @confirm_install.setter
    def confirm_install(self, value):
        if not isinstance(value, bool):
            raise DavosConfigError('confirm_install', 
                                   "field may be 'True' or 'False'")
        elif self._noninteractive and value:
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
            raise DavosConfigError('confirm_install', 
                                   "field may be 'True' or 'False'")
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
        exe_path = pathlib.Path(expandvars(exe_path)).expanduser()
        try:
            exe_path = exe_path.resolve(strict=True)
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
