"""
Module for managing session-wide global objects, switches, and
configurable options for both internal and user settings
"""

from __future__ import annotations

from typing import Literal, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ipykernel.zmqshell import ZMQInteractiveShell


__all__ = []


IPYTHON_SHELL: Optional[ZMQInteractiveShell] = None
PARSER_ENVIRONMENT: Optional[Literal['IPY_NEW', 'IPY_OLD', 'PY']] = None

CONFIRM_INSTALL = False
SUPPRESS_STDOUT = False
