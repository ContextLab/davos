from collections.abc import Iterable
from typing import Literal, NoReturn

__all__ = list[Literal['auto_restart_rerun', 'prompt_restart_rerun_buttons']]

def auto_restart_rerun(pkgs: Iterable[str]) -> NoReturn: ...
def prompt_restart_rerun_buttons(pkgs: Iterable[str]) -> None: ...
