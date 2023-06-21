from typing import Literal, TypeVar
from davos.core.core import SmuggleFunc
from davos.implementations import LineParserFunc

__all__ = list[Literal['generate_parser_func']]
_LPF = TypeVar('_LPF', bound=LineParserFunc)

def _activate_helper(smuggle_func: SmuggleFunc, parser_func: LineParserFunc) -> None: ...
def _deactivate_helper(smuggle_func: SmuggleFunc, parser_func: LineParserFunc) -> None: ...
def generate_parser_func(line_parser: _LPF) -> _LPF: ...
