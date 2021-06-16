from re import Pattern
from typing import Literal, TypedDict

__all__: list[Literal['smuggle_statement_regex']]

_pip_installed_pkgs_re: Pattern[str]
_name_re: Literal[r'[a-zA-Z]\w*']

# noinspection PyPep8Naming
class _smuggle_subexprs(TypedDict):
    as_re: Literal[r' +as +[a-zA-Z]\w*']
    comment_re: Literal[r'(?m:\#+.*$)']
    name_re: Literal[r'[a-zA-Z]\w*']
    onion_re: Literal[r'\# *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$)']
    qualname_re: Literal[r'[a-zA-Z]\w*(?: *\. *[a-zA-Z]\w*)*']

smuggle_statement_regex: Pattern[str]