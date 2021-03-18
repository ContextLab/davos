from collections.abc import Callable
from types import FunctionType
from typing import Any, Literal, Optional, Protocol, TypedDict, TypeVar
from ipykernel.zmqshell import ZMQInteractiveShell

__all__: list[Literal['Davos']]

_IPyShell = TypeVar('_IPyShell', bound=ZMQInteractiveShell)

class _SmuggleFuncProtocol(Protocol):
    def __call__(self, name: str, as_: Optional[str] = None, **kwargs: Any) -> None: ...

class SmuggleFunc(_SmuggleFuncProtocol, FunctionType):
    _register: Callable[..., None]

class LocalPkgInfo(TypedDict):
    version: str
    build: Optional[str]

class Davos:
    ipython_shell: Optional[_IPyShell]
    parser_environment: Optional[Literal['IPY_NEW', 'IPY_OLD', 'PY']]
    smuggler: SmuggleFunc
    confirm_install: bool
    suppress_stdout: bool
    smuggled: set[str]
