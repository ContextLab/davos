from typing import Literal
from types import ModuleType
from davos.core.config import DavosConfig

__all__ = list[Literal['config', 'configure', 'smuggle', 'use_default_project']]
__class__: ConfigProxyModule
__version__: str

config: DavosConfig

class ConfigProxyModule(ModuleType, DavosConfig): ...
def configure(*, active: bool = ..., auto_rerun: bool = ..., conda_env: str = ..., confirm_install: bool = ...,
              noninteractive: bool = ..., suppress_stdout: bool = ...) -> None: ...
