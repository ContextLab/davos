from argparse import Action, ArgumentParser, Namespace
from collections.abc import Sequence
from typing import Final, Literal, NoReturn

__all__ = list[Literal['EditableAction', 'OnionParser', 'pip_parser', 'SubtractAction']]

class OnionParser(ArgumentParser):
    _args: str | None
    def parse_args(self, args: Sequence[str], namespace: Namespace | None = ...) -> Namespace: ...
    def error(self, message: str) -> NoReturn: ...

class EditableAction(Action):
    def __init__(self, option_strings: Sequence[str], dest: Literal['editable'], default: bool | None = ...,
                 metavar: str | tuple[str, ...] | None = ..., help: str | None = ...) -> None: ...
    def __call__(self, parser: ArgumentParser, namespace: Namespace, values: str,
                 option_string: Literal['-e', '--editable'] | None = ...) -> None: ...

class SubtractAction(Action):
    def __init__(self, option_strings: Sequence[str], dest: str, default: object | None = ..., required: bool = ...,
                 help: str | None = ...) -> None: ...
    def __call__(self, parser: ArgumentParser, namespace: Namespace, values: None,
                 option_string: str | None = ...) -> None: ...

_pip_install_usage: list[str]
pip_parser: Final[OnionParser]
