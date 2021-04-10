"""
This module contains common utilities used by by the smuggle statement
in all three environments (Python, old IPython/Google Colab, and new
IPython/Jupyter Notebook).
"""


__all__ = ['Onion', 'prompt_input']


import re
from packaging.requirements import InvalidRequirement
from pkg_resources import (
    DistributionNotFound,
    get_distribution,
    VersionConflict
)
from subprocess import CalledProcessError

from davos import davos
from davos.exceptions import (
    InstallerError,
    OnionParserError,
    OnionSyntaxError,
    ParserNotImplementedError
)
from davos.parsers import pip_parser


class Onion:
    # ADD DOCSTRING
    @staticmethod
    def parse_onion(onion_text):
        onion_text = onion_text.lstrip('# ')
        installer, args_str = onion_text.split(':', maxsplit=1)
        # remove all space between '<installer>:' and '<args_str>'
        args_str = args_str.lstrip()
        # regex parsing to identify onion comments already ensures the
        # comment will start with "<installer>:"
        if installer == 'pip':
            parser = pip_parser
        elif installer == 'conda':
            raise ParserNotImplementedError(
                "smuggling packages via conda is not yet supported"
            )
        else:
            # theoretically not possible to get here given regex parser,
            # but include as a failsafe for completeness
            raise OnionParserError(
                "An unexpected error occurred while trying to parse onion "
                f"comment: {onion_text}"
            )
        installer_kwargs = vars(parser.parse_args(args_str.split()))
        # arg_str could potentially have both single and double quotes
        # in it, so triple quote to be safe
        return f'"{installer}"', f'"""{args_str}"""', installer_kwargs

    def __init__(self, package_name, installer, args_str, **installer_kwargs):
        # ADD DOCSTRING
        self.import_name = package_name
        if installer == 'pip':
            self.install_package = self._pip_install_package
        elif installer == 'conda':
            raise NotImplementedError(
                "smuggling packages via conda is not yet supported"
            )
        else:
            # here to handle user calling smuggle() *function* directly
            raise InstallerError(
                f"Unsupported installer: '{installer}'. Currently supported "
                "installers are:\n\t'pip'"  # and 'conda'"
            )
        self.args_str = args_str
        full_spec = installer_kwargs.pop('spec').strip("'\"")
        self.is_editable = installer_kwargs.pop('editable')
        self.verbosity = installer_kwargs.pop('verbosity')
        self.installer_kwargs = installer_kwargs
        self.build = None
        if '+' in full_spec:
            # INSTALLING FROM LOCAL/REMOTE VCS:
            #   self.install_name is the VCS program + '+' + absolute
            #   local path or remote URL, plus any optional fields
            #   (#egg=..., [#|&]subdirectory=...) except for @<ref>
            #   specifier, which is used as self.version_spec if present

            # parse out <ref> without affecting setuptools extras syntax
            _before, _sep, _after = full_spec.rpartition('@')
            if '+' in _before:
                # @<ref> was present and we split there. Get everything
                # up to #egg=..., #subdirectory=..., or end of spec
                ver_spec = _after.split('#')[0]
                # self.install_name is full spec with @<ref> removed
                self.install_name = full_spec.replace(f'@{ver_spec}', '')
                self.version_spec = f'=={ver_spec}'
            else:
                # @ either not present or used only for setuptools extra
                self.install_name = full_spec
                self.version_spec = ''
        elif '/' in full_spec:
            # INSTALLING FROM LOCAL PROJECT OR PEP 440 DIRECT REFERENCE:
            #   self.install_name is the absolute path to a local
            #   project or source archive, or the URL for a remote source
            #   archive
            self.install_name = full_spec
            self.version_spec = ''
        else:
            # INSTALLING USING A REQUIREMENT SPECIFIER:
            #   most common usage. self.install_name is package name
            #   provided in onion comment. self.version_spec is
            #   (optional) version specifier

            # split on ',' to handle multiple specs ('pkg>=1.0,<=2.0')
            first_subspec = full_spec.split(',')[0]
            for spec_delim in ('==', '<=', '>=', '!=', '~=', '<', '>', '='):
                if spec_delim in first_subspec:
                    self.install_name = full_spec[:full_spec.index(spec_delim)]
                    ver_spec = full_spec[full_spec.index(spec_delim):]
                    # if (
                    #         installer == 'conda' and
                    #         '=' in ver_spec[len(spec_delim):]
                    # ):
                    #     # if conda-installing specific build of package,
                    #     # separate build version from package version
                    #     # and handle independently
                    #     ver_spec, build = ver_spec.rsplit('=', maxsplit=1)
                    self.version_spec = ver_spec
                    break
            else:
                # no version specified with package name
                self.install_name = full_spec
                self.version_spec = ''

    @property
    def is_installed(self):
        installer_kwargs = self.installer_kwargs
        if (
                installer_kwargs.get('force_reinstall') or
                installer_kwargs.get('ignore_installed') or
                installer_kwargs.get('upgrade')
        ):
            # args that trigger install regardless of installed version
            return False
        elif self.args_str == davos.smuggled.get(self.import_name):
            # if the same version of the same package was smuggled from
            # the same source with all the same arguments previously in
            # the current interpreter session/notebook runtime (i.e.,
            # line is just being rerun)
            return True
        elif '/' not in self.install_name:
            try:
                get_distribution(self.install_name + self.version_spec)
            except (DistributionNotFound, VersionConflict, InvalidRequirement):
                # - DistributionNotFound: package is not installed
                # - VersionConflict: package is installed, but installed
                #   version doesn't fit requested version constraints
                # - InvalidRequirement: version_spec is invalid or
                #   pkg_resources couldn't parse it
                return False
            else:
                return True
        return False

    def _pip_install_package(self):
        # TODO: would be more efficient to use nullcontext here as long
        #  as it works in ipynb
        # TODO: add support for all kinds of non-index installs (see
        #  https://pip.pypa.io/en/stable/reference/pip_install/)
        install_name = self.install_name
        if '+' in install_name:
            vcs_field_sep= '#'
            if self.egg is not None:
                install_name += vcs_field_sep + self.egg
                vcs_field_sep = '&'
            if self.subdirectory is not None:
                install_name += vcs_field_sep + self.subdirectory
        elif self.version_spec is not None:
            install_name += self.version_spec
        cmd_str = f'pip install {self.installer_args} {install_name}'
        try:
            stdout, exit_code = davos.run_shell_command(cmd_str)
        except CalledProcessError as e:
            err_msg = (f"the command '{e.cmd}' returned a non-zero "
                       f"exit code: {e.returncode}. See above output "
                       f"for details")
            raise InstallerError(err_msg, e)
        else:
            return stdout, exit_code

    def _conda_install_package(self):
        raise NotImplementedError(
            "smuggling packages via conda is not yet supported"
        )


def prompt_input(prompt, default=None, interrupt=None):
    # ADD DOCSTRING
    # NOTE: interrupt applies only to shell interface, not Jupyter/Colab
    response_values = {
        'yes': True,
        'y': True,
        'no': False,
        'n': False
    }
    if interrupt is not None:
        interrupt = interrupt.lower()
        if interrupt not in response_values.keys():
            raise ValueError(
                f"'interrupt' must be one of {tuple(response_values.keys())}"
            )
    if default is not None:
        default = default.lower()
        try:
            default_value = response_values[default]
        except KeyError as e:
            raise ValueError(
                f"'default' must be one of: {tuple(response_values.keys())}"
            ) from e
        response_values[''] = default_value
        opts = '[Y/n]' if default_value else '[y/N]'
    else:
        opts = '[y/n]'

    while True:
        try:
            response = input(f"{prompt}\n{opts} ").lower()
            return response_values[response]
        except KeyboardInterrupt:
            if interrupt is not None:
                return response_values[interrupt]
            else:
                raise
        except KeyError:
            pass


_smuggle_subexprs = {
    'name_re': r'[a-zA-Z]\w*',
    'qualname_re': r'[a-zA-Z][\w.]*\w',
    'onion_re': r'\#+ *pip:.+?(?= +\#| *\n| *$)',
    'comment_re': r'(?m:\#+.*$)'
}
_smuggle_subexprs['as_re'] = fr' +as +{_smuggle_subexprs["name_re"]}'

# TODO: pattern currently doesn't enforce commas between names in
#  multiline smuggle from statement
smuggle_statement_regex = re.compile((
    r'^\s*'                                                               # match only if statement is first non-whitespace chars
    r'(?P<FULL_CMD>'                                                       # capture full text of command in named group
        r'(?:'                                                            # first valid syntax:
            r'smuggle +{qualname_re}(?:{as_re})?'                         # match 'smuggle' + pkg name + optional alias
            r'(?:'                                                        # match the following:
                r' *'                                                     #  - any amount of horizontal whitespace
                r','                                                      #  - followed by a comma
                r' *'                                                     #  - followed by any amount of horizontal whitespace
                r'{qualname_re}(?:{as_re})?'                              #  - followed by another pkg + optional alias
            r')*'                                                         # ... any number of times
            r'(?P<SEMICOLON_SEP>(?= *; *(?:smuggle|from)))?'              # check for multiple statements separated by semicolon 
                                                                          #   (matches empty string with positive lookahead assertion 
                                                                          #   so group gets defined without adding to full match)
            r'(?(SEMICOLON_SEP)|'                                         # if the aren't multiple semicolon-separated statements:
                r'(?:'
                    r' *(?={onion_re})'                                   # consume horizontal whitespace only if followed by onion
                    r'(?P<ONION>{onion_re})?'                             # capture onion comment in named group...
                r')?'                                                     # ...optionally, if present
            r')'
        r')|(?:'                                                          # else (line doesn't match valid syntax):
            r'from *{qualname_re} +smuggle +'                             # match 'from' + package[.module[...]] + 'smuggle '
            r'(?P<OPEN_PARENS>\()?'                                       # capture open parenthesis for later check, if present
            r'(?(OPEN_PARENS)'                                            # if parentheses opened:
                r'(?:'                                                    # logic for matching possible multiline statement:
                    r' *'                                                 # capture any spaces following open parenthesis
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
# ^\s*(?P<FULL_CMD>(?:smuggle +[a-zA-Z][\w.]*\w(?: +as +[a-zA-Z]\w*)?(?:
#  *, *[a-zA-Z][\w.]*\w(?: +as +[a-zA-Z]\w*)?)*(?P<SEMICOLON_SEP>(?= *;
# *(?:smuggle|from)))?(?(SEMICOLON_SEP)|(?: *(?=\#+ *pip:.+?(?= +\#| *\n
# | *$))(?P<ONION>\#+ *pip:.+?(?= +\#| *\n| *$))?)?))|(?:from *[a-zA-Z][
# \w.]*\w +smuggle +(?P<OPEN_PARENS>\()?(?(OPEN_PARENS)(?: *(?:[a-zA-Z]\
# w*(?: +as +[a-zA-Z]\w*)? *(?:, *[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*)? *)*,
# ? *)?(?:(?P<FROM_ONION_1>\#+ *pip:.+?(?= +\#| *\n| *$)) *(?m:\#+.*$)?|
# (?m:\#+.*$)|(?m:$)|(?P<CLOSE_PARENS_FIRSTLINE>\)))(?(CLOSE_PARENS_FIRS
# TLINE)|(?:\s*(?:[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*)? *(?:, *[a-zA-Z]\w*(?
# : +as +[a-zA-Z]\w*)? *)*[^)\n]*| *(?m:\#+.*$)|\n *))*\)))|[a-zA-Z]\w*(
# ?: +as +[a-zA-Z]\w*)?(?: *, *[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*)?)*)(?P<F
# ROM_SEMICOLON_SEP>(?= *; *(?:smuggle|from)))?(?(FROM_SEMICOLON_SEP)|(?
# (FROM_ONION_1)|(?: *(?=\#+ *pip:.+?(?= +\#| *\n| *$))(?P<FROM_ONION>\#
# + *pip:.+?(?= +\#| *\n| *$)))?))))