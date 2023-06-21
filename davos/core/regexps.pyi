from re import Pattern
from typing import Final, final, Literal, TypedDict

__all__ = list[Literal['pip_installed_pkgs_regex', 'smuggle_statement_regex']]

_name_re: Final[Literal[r'[a-zA-Z_]\w*']]

# noinspection PyPep8Naming
@final
class _smuggle_subexprs(TypedDict):
    as_re: Literal[r' +as +[a-zA-Z_]\w*']
    comment_re: Literal[r'(?m:\#+.*$)']
    name_re: Literal[r'[a-zA-Z_]\w*']
    onion_re: Literal[r'\# *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$)']
    qualname_re: Literal[r'[a-zA-Z_]\w*(?: *\. *[a-zA-Z_]\w*)*']

pip_installed_pkgs_regex: Final[Pattern[str]]
smuggle_statement_regex: Final[Pattern[str]]
