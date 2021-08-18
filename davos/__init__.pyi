from typing import Literal
from davos.core.config import DavosConfig

__all__ = list[
    Literal[
        'activate',
        'config',
        'configure',
        'deactivate',
        'is_active',
        'smuggle'
    ]
]
__version__: str

config: DavosConfig

def activate() -> None: ...
def configure(
        *,
        active: bool = ...,
        auto_rerun: bool = ...,
        conda_env: str = ...,
        confirm_install: bool = ...,
        noninteractive: bool = ...,
        suppress_stdout: bool = ...
) -> None: ...
def deactivate() -> None: ...
def is_active() -> bool: ...
