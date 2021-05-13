"""
# TODO: update me
This module contains common utilities used by by the smuggle statement
in all three environments (Python, old IPython/Google Colab, and new
IPython/Jupyter Notebook).
"""


__all__ = [
    'capture_stdout', 
    'Onion', 
    'prompt_input', 
    'run_shell_command', 
    'smuggle_statement_regex'
]


import importlib
import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path
from subprocess import CalledProcessError

import pkg_resources
from packaging.requirements import InvalidRequirement

from davos import config
from davos.core.exceptions import (
    InstallerError, 
    OnionParserError, 
    ParserNotImplementedError
)
from davos.core.parsers import pip_parser
from davos.implementations import _shell_cmd_helper


class capture_stdout:
    """
    Context manager similar to `contextlib.redirect_stdout`, but
    different in that it:
      - temporarily writes stdout to other streams *in addition to*
        rather than *instead of* `sys.stdout`
      - accepts any number of streams and sends stdout to each
      - can optionally keep streams open after exiting context by
        passing `closing=False`

    Parameters
    ----------
    *streams : `*io.IOBase`
        stream(s) to receive data sent to `sys.stdout`

    closing : `bool`, optional
        if [default: `True`], close streams upon exiting the context
        block.
    """
    def __init__(self, *streams, closing=True):
        self.streams = streams
        self.closing = closing
        self.sys_stdout_write = sys.stdout.write

    def __enter__(self):
        sys.stdout.write = self._write
        if len(self.streams) == 1:
            return self.streams[0]
        return self.streams

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout.write = self.sys_stdout_write
        if self.closing:
            for s in self.streams:
                s.close()

    def _write(self, data):
        for s in self.streams:
            s.write(data)
        self.sys_stdout_write(data)
        sys.stdout.flush()


class Onion:
    # ADD DOCSTRING
    @staticmethod
    def parse_onion(onion_text):
        onion_text = onion_text.lstrip('# ')
        installer, args_str = onion_text.split(':', maxsplit=1)
        # normalize whitespace
        installer = installer.strip()
        args_str = ' '.join(args_str.split()).strip()
        # regex parsing to identify onion comments already ensures the
        # comment will start with "<installer>:"
        if installer == 'pip':
            parser = pip_parser
        elif installer == 'conda':
            msg = "smuggling packages via conda is not yet supported"
            raise ParserNotImplementedError(
                msg, target_text=onion_text,
                target_offset=onion_text.index('conda')
            )
        else:
            # theoretically not possible to get here given regex parser,
            # but include as a failsafe for completeness
            msg = ("An unexpected error occurred while trying to parse onion "
                   f"comment: {onion_text}")
            raise OnionParserError(msg, target_text=onion_text)
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
        self.build = None
        self.args_str = args_str
        self.cache_key = f"{installer};{';'.join(args_str.split())}"
        if args_str == '':
            # bare smuggle statement without onion comment
            self.is_editable = False
            self.verbosity = 0
            self.installer_kwargs = {}
            self.install_name = package_name
            self.version_spec = ''
            return
        full_spec = installer_kwargs.pop('spec').strip("'\"")
        self.is_editable = installer_kwargs.pop('editable')
        self.verbosity = installer_kwargs.pop('verbosity', 0)
        self.installer_kwargs = installer_kwargs
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
        if self.import_name in config._stdlib_modules:
            # smuggled module is part of standard library
            return True
        elif (
                installer_kwargs.get('force_reinstall') or
                installer_kwargs.get('ignore_installed') or
                installer_kwargs.get('upgrade')
        ):
            # args that trigger install regardless of installed version
            return False
        elif self.args_str == config._smuggled.get(self.cache_key):
            # if the same version of the same package was smuggled from
            # the same source with all the same arguments previously in
            # the current interpreter session/notebook runtime (i.e.,
            # line is just being rerun)
            return True
        elif '/' not in self.install_name:
            full_spec = self.install_name + self.version_spec.replace("'", "")
            try:
                pkg_resources.get_distribution(full_spec)
            except pkg_resources.DistributionNotFound:
                # noinspection PyUnresolvedReferences
                # suppressed due to issue with importlib stubs in 
                # typeshed repo
                module_spec = importlib.util.find_spec(self.import_name)
                if module_spec is None:
                    # requested package is not installed
                    return False
                else:
                    # requested package is a namespace package
                    return True
            except (
                # package is installed, but installed version doesn't
                # fit requested version constraints
                pkg_resources.VersionConflict,
                # version_spec is invalid or pkg_resources couldn't
                # parse it
                InvalidRequirement
            ):
                return False
            else:
                return True
        return False

    def _conda_install_package(self):
        raise NotImplementedError(
            "smuggling packages via conda is not yet supported"
        )

    def _pip_install_package(self):
        # TODO: default behavior (no onion comment) is currently to try
        #  to simply pip-install the package name. Could raise an
        #  exception instead?
        if self.args_str == '':
            args = self.install_name
        else:
            args = self.args_str.replace("<", "'<'").replace(">", "'>'")
        cmd_str = f'pip install {args}'
        live_stdout = self.verbosity > -3
        try:
            stdout, exit_code = run_shell_command(cmd_str, 
                                                  live_stdout=live_stdout)
        except CalledProcessError as e:
            err_msg = (f"the command '{e.cmd}' returned a non-zero "
                       f"exit code: {e.returncode}. See above output "
                       f"for details")
            raise InstallerError(err_msg, e)
        # handle packages installed in non-standard locations
        install_dir = self.installer_kwargs.get('target')
        if install_dir is not None and install_dir not in sys.path:
            # make sure alternate target directory is in the module
            # search path so import machinery will find it
            sys.path.insert(0, install_dir)
        elif self.is_editable:
            install_dir = self.installer_kwargs.get('src')
            if install_dir is not None:
                # passing --src only affects editable VCS installs,
                # which are guaranteed to have #egg=<pkg_name>
                proj_name = self.install_name.split('#egg=')[1]
                # get rid of any quotes used to escape operators
                proj_name = proj_name.replace('"', '').replace("'", "")
                # only thing #egg=<pkg_name> may be followed by is
                # &subdirectory=<subdirectory>
                proj_name, _, subdir_name = proj_name.partition('&subdirectory=')
                # pip converts underscores to hyphens when naming dir
                proj_name = proj_name.replace('_', '-')
                install_dir = Path(install_dir).resolve().joinpath(proj_name,
                                                                   subdir_name)
                if install_dir not in sys.path:
                    sys.path.insert(0, str(install_dir))
        return stdout, exit_code


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


def run_shell_command(command, live_stdout=None):
    # ADD DOCSTRING
    if live_stdout is None:
        live_stdout = not config._suppress_stdout
    if live_stdout:
        command_context = capture_stdout
    else:
        command_context = redirect_stdout
    with command_context(io.StringIO()) as stdout:
        try:
            return_code = _shell_cmd_helper(command)
        except CalledProcessError as e:
            # if the exception doesn't record the output, add it
            # manually before raising
            stdout = stdout.getvalue()
            if e.output is None and stdout != '':
                e.output = stdout
            raise e
        else:
            stdout = stdout.getvalue()
    return stdout, return_code


_name_re = r'[a-zA-Z]\w*'

_smuggle_subexprs = {
    'name_re': _name_re,
    'qualname_re': fr'{_name_re}(?: *\. *{_name_re})*',
    'as_re': fr' +as +{_name_re}',
    'onion_re': r'\# *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$)',
    'comment_re': r'(?m:\#+.*$)'
}

# TODO: pattern currently doesn't enforce commas between names in
#  multiline smuggle from statement
smuggle_statement_regex = re.compile((
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
# ^\s*(?P<FULL_CMD>(?:smuggle +[a-zA-Z]\w*(?: *\. *[a-zA-Z]\w*)*(?: +as 
# +[a-zA-Z]\w*)?(?: *, *[a-zA-Z]\w*(?: *\. *[a-zA-Z]\w*)*(?: +as +[a-zA-
# Z]\w*)?)*(?P<SEMICOLON_SEP>(?= *; *(?:smuggle|from)))?(?(SEMICOLON_SEP
# )|(?: *(?=\#+ *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$))(?P<ONION
# >\#+ *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$))?)?))|(?:from *[a-
# zA-Z]\w*(?: *\. *[a-zA-Z]\w*)* +smuggle +(?P<OPEN_PARENS>\()?(?(OPEN_P
# ARENS)(?: *(?:[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*)? *(?:, *[a-zA-Z]\w*(?:
# +as +[a-zA-Z]\w*)? *)*,? *)?(?:(?P<FROM_ONION_1>\#+ *(?:pip|conda) *:
# *[^#\n ].+?(?= +\#| *\n| *$)) *(?m:\#+.*$)?|(?m:\#+.*$)|(?m:$)|(?P<CLO
# SE_PARENS_FIRSTLINE>\)))(?(CLOSE_PARENS_FIRSTLINE)|(?:\s*(?:[a-zA-Z]\w
# *(?: +as +[a-zA-Z]\w*)? *(?:, *[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*)? *)*[^
# )\n]*| *(?m:\#+.*$)|\n *))*\)))|[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*)?(?: *
# , *[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*)?)*)(?P<FROM_SEMICOLON_SEP>(?= *; *
# (?:smuggle|from)))?(?(FROM_SEMICOLON_SEP)|(?(FROM_ONION_1)|(?: *(?=\#+
#  *(?:pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$))(?P<FROM_ONION>\#+ *(?
# :pip|conda) *: *[^#\n ].+?(?= +\#| *\n| *$)))?))))
