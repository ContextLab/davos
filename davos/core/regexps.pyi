from re import Pattern
from typing import Literal, TypedDict

__all__: list[Literal['pip_installed_pkgs_regex', 'smuggle_statement_regex']]

_name_re: Literal[r'[a-zA-Z]\w*']

# noinspection PyPep8Naming
class _smuggle_subexprs(TypedDict):
    as_re: Literal[r' +as +[a-zA-Z]\w*']
    comment_re: Literal[r'(?m:\#+.*$)']
    name_re: Literal[r'[a-zA-Z]\w*']
    onion_re: Literal[r'\# *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$)']
    qualname_re: Literal[r'[a-zA-Z]\w*(?: *\. *[a-zA-Z]\w*)*']

pip_installed_pkgs_regex: Pattern[str]
smuggle_statement_regex: Pattern[str]
