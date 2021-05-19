from collections.abc import Callable
from typing import Any, Literal, NoReturn, Optional, Protocol, Union
from davos.core.config import DavosConfig, IpythonShell
from davos.core.core import PipInstallerKwargs
from davos.implementations import (
    ipython_common as ipyc, 
    ipython_post7 as ipypost, 
    ipython_pre7 as ipypre, 
    python as py
)

# TODO: add __all__

ParserFunc = Callable[[str], str]

class SmuggleFunc(Protocol):
    def __call__(
            self, 
            name: str, 
            as_: Optional[str] = ..., 
            installer: Literal['conda', 'pip'] = ..., 
            args_str: str = ..., 
            installer_kwargs: Optional[PipInstallerKwargs] = ...
    ) -> None: ...

_activate_helper: Callable[[SmuggleFunc, ParserFunc], None]
_check_conda_avail_helper: Callable[[], Optional[str]]
_deactivate_helper: Callable[[SmuggleFunc, ParserFunc], None]
_run_shell_command_helper: Callable[[str], None]
_set_custom_showsyntaxerror: Callable[[], None]

class ShowSyntaxErrorDavos(Protocol):
    def __call__(
            self, 
            ipy_shell: IpythonShell, 
            filename: Optional[str] = ..., 
            running_compiled_code: bool = ...
    ) -> None: ...

def _active_fget(conf: DavosConfig) -> bool: ...
def _active_fset(conf: DavosConfig, value: bool) -> None: ...
def _conda_avail_fget(conf: DavosConfig) -> bool: ...
def _conda_avail_fset(conf: DavosConfig, _: Any) -> NoReturn: ...
def _conda_env_fget(conf: DavosConfig) -> Optional[str]: ...
def _conda_env_fset(conf: DavosConfig, new_env: str) -> None: ...
def _conda_envs_dirs_fget(conf: DavosConfig) -> Optional[dict[str, str]]: ...
def _conda_envs_dirs_fset(conf: DavosConfig, _: Any) -> NoReturn: ...