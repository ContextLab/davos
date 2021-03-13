from typing import Literal, Optional, TypeVar
from ipykernel.zmqshell import ZMQInteractiveShell

__all__: list[str]

_IPyShell = TypeVar('_IPyShell', bound=ZMQInteractiveShell)

IPYTHON_SHELL: Optional[_IPyShell]
PARSER_ENVIRONMENT: Optional[Literal['IPY_NEW', 'IPY_OLD', 'PY']]

CONFIRM_INSTALL: bool
SUPPRESS_STDOUT: bool
