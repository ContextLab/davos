"""
This module contains common utilities used by by the `smuggle` statement
in all three environments (Python, old IPython/Google Colab, and new
IPython/Jupyter Notebook).
"""


__all__ = ['Onion', 'prompt_input']


import re
from pathlib import Path
from pkg_resources import (DistributionNotFound, find_distributions,
                           get_distribution, RequirementParseError,
                           VersionConflict)
from subprocess import CalledProcessError

from davos import davos
from davos.exceptions import InstallerError, OnionSyntaxError


class Onion:
    # ADD DOCSTRING
    @staticmethod
    def _extract_arg_value(arg_name, args_str):
        # NOTE: does not handle args with multiple space-separated values
        if arg_name not in args_str:
            return None, args_str
        pre, post = args_str.split(arg_name)
        pre = pre.strip()
        post = post.strip()
        arg_val, _, post = post.partition(' ')
        if arg_val.startswith('-') or arg_val == '':
            raise OnionSyntaxError(f"'{arg_name}' flag requires an argument")
        new_args_str = ' '.join((pre, post))
        return arg_val, new_args_str

    @staticmethod
    def parse_onion_syntax(comment_text):
        # TODO: rewrite around new regex-based line parsing
        # TODO: parse comment string for install arguments, use
        #  https://github.com/ContextLab/CDL-docker-stacks/blob/master/CI/conda_environment.py#L56-L65
        #  for splitting version string
        # TODO: handle scenario where it's an unrelated, non-onion
        #  comment
        # TODO: replace short arg versions with long versions to account
        #  for combinations, e.g. `pip install -UIt <target> package`
        # NOTE: returns a dict of {param: value} for each, CLI args that
        #  don't take a value should be ... so they don't
        #  conflict with None values in constructor
        # minimal fields that should always be in returned dict
        peeled_onion = {
            'installer': 'pip',
            'installer_args': ''
            # 'install_name': None,
            # 'version_spec': None,
            # 'egg': None,
            # 'subdirectory': None,
            # 'build': None
        }
        installer, sep, arg_str = comment_text.partition(':')
        if installer == 'conda':
            peeled_onion['installer'] = 'conda'
        elif installer != 'pip' and installer != 'pypi':
            # TODO: current smuggle_statement_regex doesn't allow this possibility
            # unrelated, non-onion inline comment
            return peeled_onion
        if sep == '':
            # TODO: current smuggle_statement_regex doesn't allow this possibility
            # no colon, no install arguments other than installer name
            return peeled_onion
        version_spec, _, arg_str = arg_str.strip().partition(' ')
        # split on ',' to account for 'pkg>=1.0,<=2.0' syntax
        first_subspec = version_spec.split(',')[0]
        for spec_delim in ('==', '<=', '>=', '!=', '~=', '<', '>', '='):
            if spec_delim in first_subspec:
                inst_name = version_spec[:version_spec.index(spec_delim)]
                ver_spec = version_spec[version_spec.index(spec_delim):]
                if installer == 'conda' and '=' in ver_spec[len(spec_delim):]:
                    # if conda-installing specific build of package,
                    # separate build version from package version and
                    # handle independently
                    ver_spec, build = ver_spec.rsplit('=', maxsplit=1)
                    peeled_onion['build'] = build
                break
        else:
            # either no version specified or installing from VCS, local
            # project, local/remote archive, wheel file, etc.
            ver_spec = None
            inst_name = version_spec
            if '+' in version_spec:
                # pip-installing from VCS (e.g., git+https://...)
                # requires special handling of --egg & --subdirectory
                # arguments that would normally be part of URL but can't
                # due to Onion format
                egg_name, arg_str = Onion._extract_arg_value('--egg', arg_str)
                subdir_path, arg_str = Onion._extract_arg_value('--subdirectory',
                                                               arg_str)
                peeled_onion['egg'] = egg_name
                peeled_onion['subdirectory'] = subdir_path
        # --editable flag must go immediately before package, so parse
        # it out so it can be placed manually later
        if '--editable' in arg_str:
            peeled_onion['editable'] = True
            arg_str = arg_str.replace('--editable', '')
        else:
            peeled_onion['editable'] = False
        peeled_onion['install_name'] = inst_name
        peeled_onion['version_spec'] = ver_spec
        peeled_onion['installer_args'] = arg_str
        return peeled_onion

    def __init__(self, import_name, installer='pip', install_name=None,
                 version_spec=None, build=None, editable=False, egg=None,
                 subdirectory=None, installer_args=''):
        # ADD DOCSTRING
        # TODO: what happens if force-reinstall, ignore-installed, etc.
        #  and module is already in sys.modules?
        if installer == 'pip' or installer == 'pypi':
            self.install_package = self._pip_install_package
        elif installer == 'conda':
            self.install_package = self._conda_install_package
        else:
            # here to handle user calling smuggle() *function* directly
            raise InstallerError(
                f"Unsupported installer: '{installer}'. Currently supported "
                "installers are 'pip' and 'conda'"
            )
        self.import_name = import_name
        self.installer = installer
        if install_name is None:
            self.install_name = import_name
        else:
            self.install_name = install_name
        self.version_spec = version_spec
        self.build = build
        self.editable = editable
        self.egg = egg
        self.subdirectory = subdirectory
        self.installer_args = installer_args

    @property
    def is_installed(self):
        # args that trigger install regardless of installed version
        if (
                '--force-reinstall' in self.installer_args or
                '--ignore-installed' in self.installer_args or
                '--upgrade' in self.installer_args
        ):
            return False
        elif self.install_name in davos.smuggled:
            if davos.smuggled[self.install_name] == self.version_spec:
                return True
            else:
                return False
        elif '+' in self.install_name:
            # unless same package, URL, & tag were already smuggled in
            # this session, installing from VCS always triggers install
            # because versions are too specific to compare reliably
            # (e.g., could install from many different git commit hashes
            # tagged with the same version)
            return False
        elif Path(self.install_name).expanduser().resolve().exists():
            # installing from local file or directory
            local_path = str(Path(self.install_name).expanduser().resolve())
            return any(find_distributions(local_path, only=True))
        else:
            dist_spec = self.install_name
            if self.version_spec is not None:
                dist_spec += self.version_spec
            try:
                get_distribution(dist_spec)
            except (DistributionNotFound, VersionConflict, RequirementParseError):
                # DistributionNotFound: package is not installed
                # VersionConflict: package is installed, but installed
                #   version doesn't fit requested version constraints
                # RequirementParserError: version_spec is invalid or
                # pkg_resources couldn't parse it
                return False
            else:
                return True

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
    'onion_re': r'\#+ *pip:[^#]+[^#\s]',
    'comment_re': r'(?m:\#+.*$)'
}
_smuggle_subexprs['as_re'] = fr' +as +{_smuggle_subexprs["name_re"]}'


smuggle_statement_regex = re.compile((
    r'^\s*'                                                               # match only if statement is first non-whitespace chars
    r'(?<FULL_CMD>'                                                       # capture full text of command in named group
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
# *(?:smuggle|from)))?(?(SEMICOLON_SEP)|(?: *(?=\#+ *pip:[^#]+[^#\s])(?P
# <ONION>\#+ *pip:[^#]+[^#\s])?)?))|(?:from *[a-zA-Z][\w.]*\w +smuggle +
# (?P<OPEN_PARENS>\()?(?(OPEN_PARENS)(?: *(?:[a-zA-Z]\w*(?: +as +[a-zA-Z
# ]\w*)? *(?:, *[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*)? *)*,? *)?(?:(?P<FROM_O
# NION_1>\#+ *pip:[^#]+[^#\s]) *(?m:\#+.*$)?|(?m:\#+.*$)|(?m:$)|(?P<CLOS
# E_PARENS>\)))(?(CLOSE_PARENS)|(?:\s*(?:[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*
# )? *(?:, *[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*)? *)*[^)\n]*| *(?m:\#+.*$)|\
# n *))*\)))|[a-zA-Z]\w*(?: +as +[a-zA-Z]\w*)?(?: *, *[a-zA-Z]\w*(?: +as
#  +[a-zA-Z]\w*)?)*)(?P<FROM_SEMICOLON_SEP>(?= *; *(?:smuggle|from)))?(?
# (FROM_SEMICOLON_SEP)|(?(FROM_ONION_1)|(?: *(?=\#+ *pip:[^#]+[^#\s])(?P
# <FROM_ONION>\#+ *pip:[^#]+[^#\s]))?))))
