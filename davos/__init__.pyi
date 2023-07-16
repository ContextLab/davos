from pathlib import PosixPath
from types import ModuleType
from typing import Final, Literal
from davos.core.config import DavosConfig
from davos.core.project import AbstractProject, ConcreteProject

__all__ = list[Literal['DAVOS_CONFIG_DIR', 'DAVOS_PROJECT_DIR', 'config', 'configure', 'get_project', 'Project',
                       'prune_projects', 'require_pip', 'require_python', 'smuggle', 'use_default_project']]
__class__: ConfigProxyModule
__version__: Final[str]

config: DavosConfig

class ConfigProxyModule(ModuleType, DavosConfig):
    @property
    def all_projects(self) -> list[AbstractProject | ConcreteProject]: ...

def configure(*, active: bool = ..., auto_rerun: bool = ..., confirm_install: bool = ..., noninteractive: bool = ...,
              pip_executable: PosixPath | str = ..., project: ConcreteProject | PosixPath | str | None = ...,
              suppress_stdout: bool = ...) -> None: ...
def require_pip(version_spec: str, warn: bool | None = ..., extra_msg: str | None = ...,
                prereleases: bool | None = ...) -> None: ...
def require_python(version_spec: str, warn: bool | None = ..., extra_msg: str | None = ...,
                   prereleases: bool | None = ...) -> None: ...
