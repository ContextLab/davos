from types import TracebackType
from typing import Callable, Optional, overload, Type, TypeVar

_T = TypeVar('_T')
_ER = Optional[_T]
_Exc = TypeVar('_Exc', bound=Exception)

class nullcontext:
    enter_result: _ER
    def __init__(self, enter_result: _ER = ...) -> None: ...
    def __enter__(self) -> _ER: ...
    @overload
    def __exit__(self, exc_type: None, exc_val: None, exc_tb: None) -> None: ...
    @overload
    def __exit__(
            self,
            exc_type: Type[_Exc],
            exc_val: _Exc,
            exc_tb: TracebackType
    ) -> None: ...
    def __exit__(
            self,
            exc_type: Optional[Type[_Exc]],
            exc_val: Optional[_Exc],
            exc_tb: Optional[TracebackType]
    ) -> None: ...

class SmuggleFunc(Callable[[str, Optional[str]], None]):
    _register_smuggler: Callable[[], None]

