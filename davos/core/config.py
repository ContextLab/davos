# ADD DOCSTRING


__all__ = ['DavosConfig']


import pathlib
import sys
import traceback
import warnings
from os.path import expandvars
from subprocess import CalledProcessError, check_output

from davos.core.exceptions import DavosConfigError, DavosError


class SingletonConfig(type):
    __instance = None

    def __call__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__call__(*args, **kwargs)
        return cls.__instance


class DavosConfig(metaclass=SingletonConfig):
    # ADD DOCSTRING
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
            # see _block_greedy_ipython_completer() docstring
            _block_greedy_ipython_completer()
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
        self._stdlib_modules = _get_stdlib_modules()
        ########################################
        #          CONFIGURABLE FIELDS         #
        ########################################
        self._active = True
        self._auto_rerun = False
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
        if (
                self._environment != 'Colaboratory' and 
                pathlib.Path(f'{sys.exec_prefix}/bin/pip').is_file()
        ):
            self._pip_executable = f'{sys.exec_prefix}/bin/pip'
        else:
            # pip exe wasn't in expected location (or it's colab, where 
            # things are all over the place)
            try:
                pip_exe = check_output(['which', 'pip'], encoding='utf-8').strip()
            except CalledProcessError:
                # try one more thing before we just throw up our hands...
                try:
                    chceck_output([sys.executable, '-c', 'import pip'])
                except CalledProcessError as e:
                    raise DavosError(
                        "Could not find 'pip' executable in $PATH or package "
                        "in 'sys.modules'"
                    ) from e
                else:
                    warnings.warn(
                        "Could not find 'pip' executable in $PATH. Falling "
                        f"back to module invokation ('{sys.executable} -m "
                        "pip'). You can fix this by setting "
                        "'davos.config.pip_executable' to your 'pip' "
                        "executable's path."
                    )
                    self._pip_executable = f'{sys.executable} -m pip'
            else:
                self._pip_executable = pip_exe

    def __repr__(self):
        # TODO: implement me
        #  also implement _repr_html_ and/or _repr_pretty_ et al.
        return super().__repr__()

    @property
    def auto_rerun(self):
        return self._auto_rerun

    @auto_rerun.setter
    def auto_rerun(self, value):
        if not isinstance(value, bool):
            raise DavosConfigError('auto_rerun',
                                   "field may be 'True' or 'False'")
        elif self._environment == 'Colaboratory':
            raise DavosConfigError(
                'auto_rerun',
                'automatic rerunning of cells not available in Colaboratory'
            )
        self._auto_rerun = value

    @property
    def confirm_install(self):
        return self._confirm_install

    @confirm_install.setter
    def confirm_install(self, value):
        # TODO: add test to check that y/n input box is displayed in
        #  plain Python & buttons are displayed in Jupyter notebook when
        #  smuggling not-installed package when confirm_install==True
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
            raise DavosConfigError('noninteractive',
                                   "field may be 'True' or 'False'")
        elif self._environment == 'Colaboratory':
            raise DavosConfigError(
                'noninteractive',
                "noninteractive mode not available in Colaboratory"
            )
        elif value and self._confirm_install:
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


def _block_greedy_ipython_completer():
    # ADD DOCSTRING - can borrow from https://github.com/ContextLab/hypertools/blob/e7b7446/hypertools/plot/backend.py#L374
    # extract 20 most recent entries. Completer module usually appears 
    # ~12 deep after davos & importlib, so add small buffer to be safe 
    # but start searching from oldest.
    stack_trace = traceback.extract_stack(limit=20)
    # drop most recent 3 frames, which are always internal davos calls
    for frame in stack_trace[:-3]:
        if frame.filename.endswith('IPython/core/completerlib.py'):
            # if stack contains calls to functions in completer module, 
            # davos was imported for greed TAB-completion. Remove 
            # davos.core & davos.core.config from sys.modules so they're 
            # reloaded when imported for real and raise generic 
            # exception to make completer function return early.
            del sys.modules['davos.core']
            del sys.modules['davos.core.config']
            raise Exception
    else:
        # davos is being imported into a non-interactive environment
        return


def _get_stdlib_modules():
    # ADD DOCSTRING
    stdlib_dir = pathlib.Path(pathlib.__file__).parent
    stdlib_modules = []
    for p in stdlib_dir.iterdir():
        if (
                (p.is_dir() and p.joinpath('__init__.py').is_file()) or
                p.suffix == '.py'
        ):
            stdlib_modules.append(p.stem)
    try:
        builtins_dir = next(d for d in sys.path if d.endswith('lib-dynload'))
    except StopIteration:
        pass
    else:
        for p in pathlib.Path(builtins_dir).glob('*.cpython*.so'):
            stdlib_modules.append(p.name.split('.')[0])
    stdlib_modules.extend(sys.builtin_module_names)
    return set(stdlib_modules)
