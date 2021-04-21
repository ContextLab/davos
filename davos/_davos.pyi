import sys
from collections.abc import Mapping
from io import StringIO
from types import TracebackType
from typing import (
    AnyStr,
    Callable,
    ClassVar,
    Generic,
    Literal,
    Optional,
    overload,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union
)
from IPython.core.interactiveshell import InteractiveShell

__all__: list[Literal['capture_stdout', 'Davos']]

_D = TypeVar('_D', bound='Davos')
_IPY_SHELL = TypeVar('_IPY_SHELL', bound=InteractiveShell)
_StringOrFileIO = Union[StringIO, TextIO]
_S = TypeVar('_S')
_S1 = Tuple[_StringOrFileIO]
_SN = Tuple[_StringOrFileIO, ...]
_E = TypeVar('_E', bound=BaseException)

class Davos:
    __instance: ClassVar[Optional[_D]]
    _ipython_showsyntaxerror_orig: Callable[[_IPY_SHELL, Optional[str]], None]
    _shell_cmd_helper: Callable[[str], int]
    activate_parser: Callable[[], None]
    confirm_install: bool
    deactivate_parser: Callable[[], None]
    ipython_shell: _IPY_SHELL
    parser_environment: Literal['IPY_NEW', 'IPY_OLD', 'PY']
    parser_is_active: Callable[[], bool]
    smuggled: dict[str, str]
    smuggler: Callable[[str, Optional[str], Literal['pip'], str, Optional[Mapping]], None]
    suppress_stdout: bool
    def __new__(cls: Type[Davos]) -> _D: ...
    def initialize(self) -> None: ...
    def run_shell_command(self, command: str, live_stdout: Optional[bool] = None) -> tuple[str, int]: ...

class capture_stdout(Generic[_S]):
    closing: bool
    streams: _S
    sys_stdout_write: sys.stdout.write
    def __init__(self, *streams: _StringOrFileIO, closing: bool = True) -> None: ...
    @overload
    def __enter__(self: capture_stdout[_S1]) -> _StringOrFileIO: ...
    @overload
    def __enter__(self: capture_stdout[_SN]) -> _SN: ...
    @overload
    def __exit__(self, exc_type: None, exc_value: None, traceback: None) -> None: ...
    @overload
    def __exit__(self, exc_type: Type[_E], exc_value: _E, traceback: TracebackType) -> bool: ...
    def _write(self, data: AnyStr) -> None: ...
