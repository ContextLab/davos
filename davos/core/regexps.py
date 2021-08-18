"""
This module contains regular expressions used heavily by `davos`,
pre-compiled as `re.Pattern` objects.
"""


__all__ = ['pip_installed_pkgs_regex', 'smuggle_statement_regex']


import re


_name_re = r'[a-zA-Z_]\w*'    # pylint: disable=invalid-name

_smuggle_subexprs = {
    'name_re': _name_re,
    'qualname_re': fr'{_name_re}(?: *\. *{_name_re})*',
    'as_re': fr' +as +{_name_re}',
    'onion_re': r'\# *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$)',
    'comment_re': r'(?m:\#+.*$)'
}

pip_installed_pkgs_regex = re.compile("^Successfully installed (.*)$",
                                      re.MULTILINE)

# pylint: disable=line-too-long, trailing-whitespace
smuggle_statement_regex = re.compile((    # noqa: E131
    r'^\s*'                                                               # match only if statement is first non-whitespace chars
    r'(?P<FULL_CMD>'                                                      # capture full text of command in named group
        r'(?:'                                                            # first valid syntax:
            r'smuggle +{qualname_re}(?:{as_re})?'                         # match 'smuggle' + pkg/module name + optional alias
            r'(?:'                                                        # match the following:
                r' *'                                                     #  - any amount of horizontal whitespace
                r','                                                      #  - followed by a comma
                r' *'                                                     #  - followed by any amount of horizontal whitespace
                r'{qualname_re}(?:{as_re})?'                              #  - followed by another pkg + optional alias
            r')*'                                                         # ... any number of times
            r'(?P<SEMICOLON_SEP>(?= *; *(?:smuggle|from)))?'              # check for multiple statements separated by semicolon 
                                                                          #   (match empty string with positive lookahead assertion 
                                                                          #   so named group gets defined without consuming)
            r'(?(SEMICOLON_SEP)|'                                         # if the aren't multiple semicolon-separated statements:
                r'(?:'
                    r' *(?={onion_re})'                                   # consume horizontal whitespace only if followed by onion
                    r'(?P<ONION>{onion_re})?'                             # capture onion comment in named group...
                r')?'                                                     # ...optionally, if present
            r')'
        r')|(?:'                                                          # else (line doesn't match first valid syntax):
            r'from *{qualname_re} +smuggle +'                             # match 'from' + package[.module[...]] + 'smuggle '
            r'(?P<OPEN_PARENS>\()?'                                       # capture open parenthesis for later check, if present
            r'(?(OPEN_PARENS)'                                            # if parentheses opened:
                r'(?:'                                                    # logic for matching possible multiline statement:
                    r' *'                                                 # capture any spaces following opening parenthesis
                    r'(?:'                                                # logic for matching code on *first line*:
                        r'{name_re}(?:{as_re})?'                          # match a name with optional alias
                        r' *'                                             # optionally, match any number of spaces
                        r'(?:'                                            # match the following...:
                            r','                                          #  - a comma
                            r' *'                                         #  - optionally followed by any number of spaces
                            r'{name_re}(?:{as_re})?'                      #  - followed by another name with optional alias
                            r' *'                                         #  - optionally followed by any number of spaces
                        r')*'                                             # ...any number of times
                        r',?'                                             # match optional comma after last name, however many there were
                        r' *'                                             # finally, match any number of optional spaces
                    r')?'                                                 # any code on first line (matched by preceding group) is optional
                    r'(?:'                                                # match 1 of 4 possible ends for first line:
                        r'(?P<FROM_ONION_1>{onion_re}) *{comment_re}?'    #  1. onion, optionally followed by unrelated comment(s)
                    r'|'                                                  #
                        r'{comment_re}'                                   #  2. unrelated, non-onion comment
                    r'|'                                                  #
                        r'(?m:$)'                                         #  3. nothing further before EOL
                    r'|'                                                  #
                        r'(?P<CLOSE_PARENS_FIRSTLINE>\))'                 #  4. close parenthesis on first line
                    r')'
                    r'(?(CLOSE_PARENS_FIRSTLINE)|'                        # if parentheses were NOT closed on first line
                        r'(?:'                                            # logic for matching subsequent line(s) of multiline smuggle statement:
                            r'\s*'                                        # match any & all whitespace before 2nd line
                            r'(?:'                                        # match 1 of 3 possibilities for each additional line:
                                r'{name_re}(?:{as_re})?'                  #  1. similar to first line, match a name & optional alias...
                                r' *'                                     #     ...followed by any amount of horizontal whitespace...
                                r'(?:'                                    #     ...
                                    r','                                  #     ...followed by comma...
                                    r' *'                                 #     ...optional whitespace...
                                    r'{name_re}(?:{as_re})?'              #     ...additional name & optional alias
                                    r' *'                                 #     ...optional whitespace...
                                r')*'                                     #     ...repeated any number of times
                                r'[^)\n]*'                                #     ...plus any other content up to newline or close parenthesis
                            r'|'
                                r' *{comment_re}'                         #  2. match full-line comment, indented an arbitrary amount
                            r'|'
                                r'\n *'                                   #  3. an empty line (truly empty or only whitespace characters)
                            r')'
                        r')*'                                             # and repeat for any number of additional lines
                        r'\)'                                             # finally, match close parenthesis
                    r')'
                r')'
            r'|'                                                          # else (no open parenthesis, so single line or /-continuation):
                r'{name_re}(?:{as_re})?'                                  # match name with optional alias
                r'(?:'                                                    # possibly with additional comma-separated names & aliases ...
                    r' *'                                                 # ...
                    r','                                                  # ...
                    r' *'                                                 # ...
                    r'{name_re}(?:{as_re})?'                              # ...
                r')*'                                                     # ...repeated any number of times
            r')'
            r'(?P<FROM_SEMICOLON_SEP>(?= *; *(?:smuggle|from)))?'         # check for multiple statements separated by semicolon
            r'(?(FROM_SEMICOLON_SEP)|'                                    # if there aren't additional ;-separated statements...
                r'(?(FROM_ONION_1)|'                                      # ...and this isn't a multiline statement with onion on line 1:
                    r'(?:'
                        r' *(?={onion_re})'                               # consume horizontal whitespace only if followed by onion
                        r'(?P<FROM_ONION>{onion_re})'                     # capture onion comment in named group...
                    r')?'                                                 # ...optionally, if present
                r')'
            r')'
        r')'
    r')'
).format_map(_smuggle_subexprs))

# Condensed, fully substituted regex:
# ^\s*(?P<FULL_CMD>(?:smuggle +[a-zA-Z_]\w*(?: *\. *[a-zA-Z_]\w*)*(?: +a
# s +[a-zA-Z_]\w*)?(?: *, *[a-zA-Z_]\w*(?: *\. *[a-zA-Z_]\w*)*(?: +as +[
# a-zA-Z_]\w*)?)*(?P<SEMICOLON_SEP>(?= *; *(?:smuggle|from)))?(?(SEMICOL
# ON_SEP)|(?: *(?=\# *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$))(?P<
# ONION>\# *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$))?)?))|(?:from
# *[a-zA-Z_]\w*(?: *\. *[a-zA-Z_]\w*)* +smuggle +(?P<OPEN_PARENS>\()?(?(
# OPEN_PARENS)(?: *(?:[a-zA-Z_]\w*(?: +as +[a-zA-Z_]\w*)? *(?:, *[a-zA-Z
# _]\w*(?: +as +[a-zA-Z_]\w*)? *)*,? *)?(?:(?P<FROM_ONION_1>\# *(?:pip|c
# onda) *: *[^#\n ].+?(?= +\#| *\n| *$)) *(?m:\#+.*$)?|(?m:\#+.*$)|(?m:$
# )|(?P<CLOSE_PARENS_FIRSTLINE>\)))(?(CLOSE_PARENS_FIRSTLINE)|(?:\s*(?:[
# a-zA-Z_]\w*(?: +as +[a-zA-Z_]\w*)? *(?:, *[a-zA-Z_]\w*(?: +as +[a-zA-Z
# _]\w*)? *)*[^)\n]*| *(?m:\#+.*$)|\n *))*\)))|[a-zA-Z_]\w*(?: +as +[a-z
# A-Z_]\w*)?(?: *, *[a-zA-Z_]\w*(?: +as +[a-zA-Z_]\w*)?)*)(?P<FROM_SEMIC
# OLON_SEP>(?= *; *(?:smuggle|from)))?(?(FROM_SEMICOLON_SEP)|(?(FROM_ONI
# ON_1)|(?: *(?=\# *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$))(?P<FR
# OM_ONION>\# *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$)))?))))
