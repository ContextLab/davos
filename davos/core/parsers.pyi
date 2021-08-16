from argparse import Action, ArgumentParser, Namespace
from collections.abc import Sequence
from typing import Any, Literal, NoReturn, Optional, Tuple, Union

__all__ = list[Literal['EditableAction', 'OnionParser', 'pip_parser', 'SubtractAction']]

class OnionParser(ArgumentParser):
    _args: Optional[str]
    def parse_args(                                              # type: ignore
            self,
            args: Sequence[str],
            namespace: Optional[Namespace] = ...
    ) -> Namespace: ...
    def error(self, message: str) -> NoReturn: ...

class EditableAction(Action):
    def __init__(
            self,
            option_strings: Sequence[str],
            dest: Literal['editable'],
            default: Optional[bool] = ...,
            metavar: Optional[Union[str, Tuple[str, ...]]] = ...,
            help: Optional[str] = ...
    ) -> None: ...
    def __call__(
            self,
            parser: ArgumentParser,
            namespace: Namespace,
            values: str,
            option_string: Optional[Literal['-e', '--editable']] = ...
    ) -> None: ...

class SubtractAction(Action):
    def __init__(
            self,
            option_strings: Sequence[str],
            dest: str,
            default: Optional[Any] = ...,
            required: bool = ...,
            help: Optional[str] = ...
    ) -> None: ...
    def __call__(
            self,
            parser: ArgumentParser,
            namespace: Namespace,
            values: None,
            option_string: Optional[str] = ...
    ) -> None: ...

_pip_install_usage: list[str]
pip_parser: OnionParser
