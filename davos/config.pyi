from typing import Literal, Optional
from ipykernel.zmqshell import ZMQInteractiveShell

__all__: list

IPYTHON_SHELL: Optional[ZMQInteractiveShell]
PARSER_ENVIRONMENT: Optional[Literal['IPY_NEW', 'IPY_OLD', 'PY']]
CURR_INSTALL_NAME: Optional[str]
CONFIRM_INSTALL: bool
SUPPRESS_STDOUT: bool