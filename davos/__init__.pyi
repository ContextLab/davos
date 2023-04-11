from pathlib import PosixPath
from types import ModuleType
from typing import Literal
from davos.core.config import DavosConfig
from davos.core.project import ConcreteProject

__all__ = list[Literal['config', 'configure', 'smuggle', 'use_default_project']]
__class__: ConfigProxyModule
__version__: str

config: DavosConfig

class ConfigProxyModule(ModuleType, DavosConfig): ...
def configure(*, active: bool = ..., auto_rerun: bool = ..., conda_env: str = ..., confirm_install: bool = ...,
              noninteractive: bool = ..., pip_executable: PosixPath | str = ...,
              project: ConcreteProject | PosixPath | str | None = ..., suppress_stdout: bool = ...) -> None: ...
