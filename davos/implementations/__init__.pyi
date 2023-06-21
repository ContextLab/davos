from collections.abc import Callable
from pathlib import PosixPath
from typing import Final, Literal, NoReturn, Protocol
from davos.core.config import DavosConfig
from davos.core.core import SmuggleFunc

__all__ = list[Literal['auto_restart_rerun', 'full_parser', 'generate_parser_func', 'prompt_restart_rerun_buttons']]

class IPyPost7FullParserFunc(Protocol):
    has_side_effects: Literal[True]
    def __call__(self, lines: list[str]) -> list[str]: ...

LineParserFunc = Callable[[str], str]
FullParserFunc = LineParserFunc | IPyPost7FullParserFunc

_activate_helper: Callable[[SmuggleFunc, FullParserFunc], None]
_check_conda_avail_helper: Callable[[], str | None]
_deactivate_helper: Callable[[SmuggleFunc, FullParserFunc], None]
_run_shell_command_helper: Callable[[str], None]
_set_custom_showsyntaxerror: Callable[[], None]
auto_restart_rerun: Callable[[list[str]], NoReturn]
full_parser: FullParserFunc
generate_parser_func: Callable[[LineParserFunc], FullParserFunc]
import_environment: Final[Literal['Colaboratory', 'IPython<7.0', 'IPython>=7.0', 'Python']]
prompt_restart_rerun_buttons: Callable[[list[str]], object | None]

def _active_fget(conf: DavosConfig) -> bool: ...
def _active_fset(conf: DavosConfig, value: bool) -> None: ...
def _conda_avail_fget(conf: DavosConfig) -> bool: ...
def _conda_avail_fset(conf: DavosConfig, _: object) -> NoReturn: ...
def _conda_env_fget(conf: DavosConfig) -> str | None: ...
def _conda_env_fset(conf: DavosConfig, new_env: PosixPath | str) -> None: ...
def _conda_envs_dirs_fget(conf: DavosConfig) -> dict[str, str] | None: ...
def _conda_envs_dirs_fset(conf: DavosConfig, _: object) -> NoReturn: ...
