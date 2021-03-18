from collections.abc import Callable
from types import FunctionType
from typing import (Any, ClassVar, Literal, Optional, Protocol, TypedDict,
                    TypeVar)
from ipykernel.zmqshell import ZMQInteractiveShell

__all__: list[Literal['Davos']]

_IPyShell = TypeVar('_IPyShell', bound=ZMQInteractiveShell)
_Davos = TypeVar('_Davos', bound='Davos')

class _SmuggleFuncProtocol(Protocol):
    def __call__(self, name: str, as_: Optional[str] = None, **kwargs: Any) -> None: ...

class SmuggleFunc(_SmuggleFuncProtocol, FunctionType):
    _register: Callable[..., None]

class LocalPkgInfo(TypedDict):
    version: str
    build: Optional[str]

class Davos:
    __instance: ClassVar[Optional[_Davos]]
    _shell_cmd_helper: Callable[[str], int]
    confirm_install: bool
    ipython_shell: Optional[_IPyShell]
    parser_environment: Literal['IPY_NEW', 'IPY_OLD', 'PY']
    smuggled: dict[str, Optional[str]]
    smuggler: SmuggleFunc
    suppress_stdout: bool
    def __new__(cls) -> _Davos: ...
    def initialize(self) -> None: ...
    def run_shell_command(self, command: str, live_stdout: Optional[bool] = ...) -> tuple[str, int]: ...