from collections.abc import Callable
from typing import (
    Any, 
    ClassVar, 
    Final, 
    Literal, 
    NoReturn, 
    Optional, 
    TypeVar, 
    Union
)
from ipykernel.zmqshell import ZMQInteractiveShell

__all__: list[Literal['DavosConfig']]

_Environment = Literal['Colaboratory', 'IPython<7.0', 'IPython>=7.0', 'Python']
_IpyShell = TypeVar('_IpyShell', bound=ZMQInteractiveShell)
_IpyShowSyntaxErrorPre7 = Callable[[_IpyShell, Optional[str]], None]
_IpyShowSyntaxErrorPost7 = Callable[[_IpyShell, Optional[str], bool], None]

class SingletonConfig(type):
    __instance: ClassVar[Optional[DavosConfig]]
    def __call__(cls, *args, **kwargs) -> DavosConfig: ...
    
class DavosConfig(metaclass=SingletonConfig):
    _active: bool
    _allow_rerun: bool
    _confirm_install: bool
    _environment: Final[_Environment]
    _ipy_showsyntaxerror_orig: Final[Optional[Union[_IpyShowSyntaxErrorPre7, _IpyShowSyntaxErrorPost7]]]
    _ipython_shell: Final[Optional[_IpyShell]]
    _smuggled: dict[str: str]
    _stdlib_modules: Final[set[str]]
    _suppress_stdout: bool
    @staticmethod
    def _get_stdlib_modules() -> set[str]: ...
    def __init__(self) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def active(self) -> bool: ...
    @active.setter
    def active(self, state: bool) -> None: ...
    @property
    def allow_rerun(self) -> bool: ...
    @allow_rerun.setter
    def allow_rerun(self, value: bool) -> None: ...
    @property
    def confirm_install(self) -> bool: ...
    @confirm_install.setter
    def confirm_install(self, value: bool) -> None: ...
    @property
    def environment(self) -> _Environment: ...
    @environment.setter
    def environment(self, _: Any) -> NoReturn: ...
    @property
    def ipython_shell(self) -> Optional[_IpyShell]: ...
    @ipython_shell.setter
    def ipython_shell(self, _: Any) -> NoReturn: ...
    @property
    def smuggled(self) -> _Environment: ...
    @smuggled.setter
    def smuggled(self, _: Any) -> NoReturn: ...
    @property
    def suppress_stdout(self) -> bool: ...
    @suppress_stdout.setter
    def suppress_stdout(self, value) -> None: ...