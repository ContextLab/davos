"""
This module implements the 'smuggle' statement for interactive Python
environments built on top of IPython<7.0.0 (released 9/27/2018).

This implementation will most commonly be used in Google Colaboratory
notebooks (hence the module name), which as of 3/9/2021 run IPython
v5.5.0. However, IPython shells & Jupyter notebooks running older
versions of IPython will also use this approach
"""


__all__ = [
    'register_smuggler_colab',
    'run_shell_command_colab',
    'smuggle_colab'
]


import importlib
import re
import sys
import warnings
from subprocess import CalledProcessError

from davos import davos
from davos.core import Onion, prompt_input, smuggle_statement_regex
from davos.exceptions import DavosParserError, OnionTypeError, SmugglerError

if davos.ipython_shell is not None:
    from IPython.core.display import _display_mimetype
    from IPython.core.inputtransformer import StatelessInputTransformer
    from IPython.core.interactiveshell import system as _run_shell_cmd
    from IPython.utils.importstring import import_item
    # additional check to make sure this is in Colab notebook rather
    # than just very old IPython kernel
    from ipykernel.zmqshell import ZMQInteractiveShell
    if type(davos.ipython_shell) is not ZMQInteractiveShell:
        # noinspection PyUnresolvedReferences
        from google.colab._pip import (
            _previously_imported_packages as get_updated_imported_pkgs
        )


def register_smuggler_colab():
    """
    adds the smuggle_inspector function to IPython's list of
    InputTransformers that get called on the contents of each code cell.

    NOTE: there are multiple different groups of InputTransformers that
        IPython runs on cell content at different pre-execution stages,
        between the various steps of the IPython parser. We're adding
        the smuggle_inspector as a "python_line_transform" which runs
        after the last step of the IPython parser, but before the code
        is passed off to the Python parser. At this point, the IPython
        parser has reassembled both explicit (backslash-based) and
        implicit (parentheses-based) line continuations, so long smuggle
        statements broken into multiple lines by either method will be
        passed to the smuggle_inspector as a single line
    """
    colab_shell = davos.ipython_shell
    smuggle_transformer = StatelessInputTransformer.wrap(smuggle_parser_colab)
    # entire IPython.core.inputsplitter module was deprecated in v7.0.0,
    # but Colab runs v5.5.0, so we still have to register our
    # transformer in both places for it to work correctly
    # noinspection PyDeprecation
    colab_shell.input_splitter.python_line_transforms.append(smuggle_transformer())
    colab_shell.input_transformer_manager.python_line_transforms.append(smuggle_transformer())
    colab_shell.user_ns['smuggle'] = smuggle_colab


def run_shell_command_colab(command):
    # much simpler than plain Python equivalent b/c IPython has a
    # built-in utility function for running shell commands that handles
    # pretty much everything we need it to, and also formats outputs
    # nicely in the notebook
    retcode = _run_shell_cmd(command)
    if retcode != 0:
        raise CalledProcessError(returncode=retcode, cmd=command)
    return retcode


def smuggle_colab(name, as_=None, **onion_kwargs):
    # ADD DOCSTRING
    # NOTE: 'name' can be a package, subpackage, module or object
    # TODO: move this name splitting logic somewhere else where it's cleaner
    if not any(char in name for char in ('+', '/', ':')):
        # dirty way of excluding names for VCS & local/remote files/modules
        pkg_name = name.split('.')[0]
    else:
        pkg_name = name
    try:
        onion = Onion(pkg_name, **onion_kwargs)
    except TypeError as e:
        # TODO(?): find a way to *replace* exception. still shows last
        #  frame of old traceback
        raise OnionTypeError(*e.args).with_traceback(e.__traceback__) from None

    if onion.is_installed:
        try:
            imported_obj = import_item(name)
        except ModuleNotFoundError as e:
            # TODO: check for --yes (conda, also pip?) and bypass if passed
            if davos.confirm_install:
                msg = (f"package {name} is not installed.  Do you want to "
                       "install it?")
                install_pkg = prompt_input(msg, default='n')
                if not install_pkg:
                    raise e
            else:
                install_pkg = True
        else:
            install_pkg = False
    else:
        install_pkg = True

    if install_pkg:
        installer_stdout, exit_code = onion.install_package()
        # packages with C extensions (e.g., numpy, pandas) cannot be
        # reloaded within an interpreter session. If the package was
        # previously imported in the current runtime (even if not by
        # user), get versions before & after reload, and if there's no
        # change, warn about needing to reset runtime for changes to
        # take effect with "RESTART RUNTIME" button in output. Elif
        # unable to determine version both before and after reload,
        # issue lower-priority warning about uncertainty
        prev_imported_pkgs = get_updated_imported_pkgs(installer_stdout)
        # highest-level package should be dealt with last
        try:
            prev_imported_pkgs.remove(pkg_name)
        except ValueError:
            check_smuggled_pkg = False
        else:
            check_smuggled_pkg = True
        for pkg_name in prev_imported_pkgs:
            # imported_pkgs_updated computes intersection with
            # set(sys.modules), so names are guaranteed to be there
            importlib.reload(sys.modules[pkg_name])
        if check_smuggled_pkg:
            old_pkg = sys.modules[pkg_name]
            try:
                old_version = old_pkg.__version__
            except AttributeError:
                old_version = None
            new_pkg = importlib.reload(old_pkg)
            try:
                new_version = new_pkg.__version__
            except AttributeError:
                new_version = None
            if old_version == new_version:
                if old_version is new_version is None:
                    warnings.warn(
                        "Failed to programmatically package version of "
                        f"previously imported package '{pkg_name}' both before "
                        "and after smuggling. If this module contains C "
                        "extensions, you may need to restart the runtime to "
                        "use the newly installed version"
                    )
                elif onion.version_spec is not None:
                    # casting the widest net possible for this edge
                    # case: if specific version not provided, old & new
                    # package versions are likely to be the same (e.g.,
                    # VCS/local/archive/forced/etc. install) and since
                    # user can see the pip-install command's output,
                    # probably better to be conservative about issuing
                    # big, bright red warnings. Also adding
                    # `davos.confirm_installed_versions()` for more
                    # aggressive checking,
                    _display_mimetype(
                        "application/vnd.colab-display-data+json",
                        (
                            {'pip_warning': {'packages': pkg_name}},
                        ),
                        raw=True
                    )
        imported_obj = import_item(name)
    # import_item takes care of adding package to sys.modules (& its
    # parents if it's a subpackage), but doesn't add the module
    # name/alias to globals() like the normal import statement
    if as_ is None:
        if name == pkg_name:
            davos.ipython_shell.user_ns[name] = sys.modules[name]
        else:
            davos.ipython_shell.user_ns[name] = imported_obj
    else:
        davos.ipython_shell.user_ns[as_] = imported_obj
    davos.smuggled[onion.install_name] = onion.version_spec


def smuggle_parser_colab(line):
    # ADD DOCSTRING
    match = smuggle_statement_regex.match(line)
    if match is None:
        return line

    matched_groups = match.groupdict()
    smuggle_chars = matched_groups['FULL_CMD']
    before_chars, after_chars = line.split(smuggle_chars)
    cmd_prefix, to_smuggle = smuggle_chars.split('smuggle ', maxsplit=1)

    if cmd_prefix:
        # cmd_prefix == 'from <package[.module[...]]> '
        is_from_statement = True
        onion_chars = matched_groups['FROM_ONION'] or matched_groups['FROM_ONION_1']
        has_semicolon_sep = matched_groups['FROM_SEMICOLON_SEP'] is not None
        pkg_name = cmd_prefix.split()[1] + '.'
        to_smuggle = re.sub(r'[()]|\s*\#.*$\s*', ' ', to_smuggle, flags=re.MULTILINE)
        to_smuggle = to_smuggle.rstrip(', ')
    else:
        # cmd_prefix == ''
        is_from_statement = False
        onion_chars = matched_groups['ONION']
        has_semicolon_sep = matched_groups['SEMICOLON_SEP'] is not None

    kwargs_str = ''
    if has_semicolon_sep:
        after_chars = '; ' + smuggle_parser_colab(after_chars.lstrip('; '))
    elif onion_chars is not None:
        to_smuggle = to_smuggle.replace(onion_chars, '').rstrip()
        onion_kwargs = Onion.parse_onion_syntax(onion_chars.lstrip('# '))
        for arg, val in onion_kwargs.items():
            if isinstance(val, str):
                val = f'"{val}"'
            kwargs_str += f', {arg}={val}'

    smuggle_funcs = []
    names_aliases = to_smuggle.split(',')
    for na in names_aliases:
        if ' as ' in na:
            name, alias = na.split(' as ')
            name = '"' + name.strip() + '"'
            alias = '"' + alias.strip() + '"'
        else:
            na = na.strip()
            if is_from_statement:
                name = '"' + cmd_prefix.split()[1] + '.' + na + '"'
                alias = '"' + na + '"'
            else:
                name = '"' + na + '"'
                alias = None
        smuggle_funcs.append(f'smuggle(name={name}, as_={alias})')
    smuggle_funcs[0] = smuggle_funcs[0][:-1] + kwargs_str + ')'
    return before_chars + '; '.join(smuggle_funcs) + after_chars

#
# def smuggle_parser_colab(line):
#     # ADD DOCSTRING
#     stripped = line.strip()
#     if 'smuggle ' not in line:# or (not stripped.startswith('smuggle') and ):
#         return line
#
#     indent_len = len(line) - len(line.lstrip(' '))
#     if '#' in stripped:
#         if stripped.index('#') < stripped.index('smuggle '):
#             return line
#         elif all(c in stripped for c in '()\n'):
#             # - handles syntax for using a single statement to smuggle
#             #   multiple items joined via implicit line continuation
#             #   inside parentheses, e.g.:
#             #    ```
#             #    smuggle (a,    # pkg a onion comment # unrelated comment
#             #             b,    # pkg b onion comment
#             #             c)    # pkg c onion comment
#             #
#             #    smuggle (      # unrelated comment here is valid
#             #        d,         # pkg d onion comment
#             #        e,     # can be any amount of space before comment
#             #    # comments between lines are also valid
#             #        f          # pkg f onion comment
#             #    )              # unrelated comment here also valid
#             #
#             #    from g smuggle (    # pkg g onion comment
#             #        h,
#             #        i,
#             #        j
#             #    )
#             #    ```
#             # - Multiline statements are only possible using implicit
#             # line continuation. Backslash continuation gets passed to
#             # transformer as a single line
#             if stripped.startswith('smuggle'):
#                 # If items are different packages, each could have its
#                 # own onion comment
#                 sub_lines = []
#                 for _line in stripped.splitlines():
#                     code, sep, comment = _line.partition('#')
#                     code = code.strip(', ')
#                     if code.endswith('(') or code == '' or code == ')':
#                         # - skip empty first lines, i.e. 'smuggle ('
#                         # - skip lines with no code, just comments
#                         # - skip empty last lines, i.e. ')'
#                         continue
#                     else:
#                         _line = f"smuggle {code.strip('() ')} {sep} {comment}"
#                         sub_lines.append(smuggle_parser_colab(_line))
#             elif stripped.startswith('from '):
#                 # multiline import of items from the same package can
#                 # have only a single onion comment. Can go on either the
#                 # first line (preferred) or last line (also allowed).
#                 # NOTE: if there is ANY comment on the first line, even
#                 #  if it is not an onion notation, the last line will
#                 #  not be looked at
#                 _lines = stripped.splitlines()
#                 code, _, comment = _lines[0].partition('#')
#                 pkg_name = code.split()[1]
#                 comment = comment.strip()
#                 if comment == '':
#                     comment = _lines[-1].partition('#')[2].strip()
#                 if comment == '':
#                     sep = ''
#                 else:
#                     sep = ' # '
#                 sub_lines = []
#                 _lines = stripped.split('smuggle (')[1].splitlines()
#                 for _line in _lines:
#                     _line = _line.split('#')[0].strip('), ')
#                     for name in _line.split(','):
#                         if name != '':
#                             _cmd = f'from {pkg_name} smuggle {name}'
#                             sub_lines.append(_cmd)
#                 # add onion comment to first statement so package
#                 # exists when the rest are run
#                 sub_lines[0] = f'{sub_lines[0]}{sep}{comment}'
#                 sub_lines = list(map(smuggle_parser_colab, sub_lines))
#             else:
#                 raise DavosParserError(
#                     "failed to parse multiline smuggle statement"
#                 )
#             line = '; '.join(sub_lines)
#         else:
#             # otherwise, there's only one onion comment
#             # TODO: a way to catch this, which is invalid and normally
#             #  raises a SyntaxError:
#             #   ```
#             #   import a, \  # a onion comment
#             #          b, \  # b onion comment
#             #          c,    # c onion comment
#             #   ```
#             stripped, _, raw_onion = stripped.partition('#')
#             stripped = stripped.strip()
#             # currently in form: `smuggle(pack.age, as_=['<alias>'|None])`
#             base_smuggle_call = smuggle_parser_colab(stripped)
#             # drop any trailing non-onion comments
#             raw_onion = raw_onion.partition('#')[0]
#             # {param: value} kwargs dict for smuggle_colab()
#             peeled_onion = Onion.parse_onion_syntax(raw_onion)
#             kwargs_list = []
#             for k, v in peeled_onion.items():
#                 if isinstance(v, str):
#                     v = '"' + v + '"'
#                 kwargs_list.append(f'{k}={v}')
#             kwargs_fmt = ', '.join(kwargs_list)
#             # insert the kwargs before the closing parenthesis
#             line = f"{base_smuggle_call[:-1]}, {kwargs_fmt})"
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#         elif ';' in stripped:
#             # handles semicolon-separated smuggle calls, e.g.:
#             #   `smuggle os.path; from pathlib smuggle Path; smuggle re`
#             # by running function on each call individually & re-joining
#             line = '; '.join(map(smuggle_parser_colab, stripped.split(';')))
#         elif ',' in stripped:
#             # handles comma-separated list of packages/modules/functions
#             # to smuggle
#             if stripped.startswith('from '):
#                 # smuggling multiple names from same package, e.g.:
#                 #   `from os.path smuggle dirname, join as opj, realpath`
#                 # is transformed internally into multiple smuggle calls:
#                 #   `smuggle os.path.dirname as dirname; smuggle os....`
#                 from_cmd, names = stripped.split(' smuggle ')
#                 names = names.strip('()\n\t ').split(',')
#                 all_cmds = [f'{from_cmd} smuggle {name}' for name in names]
#             else:
#                 # smuggling multiple packages at once, e.g.:
#                 #   `smuggle collections.abc as abc, json, os`
#                 # is transformed into multiple smuggle calls, e.g.:
#                 #   `smugle collections.abc as abc; smuggle json, sm...`
#                 names = stripped.replace('smuggle ', '').split(',')
#                 all_cmds = [f'smuggle {name}' for name in names]
#             line = '; '.join(map(smuggle_parser_colab, all_cmds))
#         elif stripped.startswith('from '):
#             # handles smuggle calls in formats like, e.g.:
#             #   `from os.path smuggle join as opj`
#             # by transforming them into, e.g.:
#             #   `smuggle os.path.join as opj
#             # This grammar can sometimes fail with the builtin import
#             # statement, e.g.:
#             #   `import numpy.array as array` # -> ModuleNotFoundError
#             # but IPython.utils.importstring.import_item always succeeds
#             pkg_name, name = stripped.split(' smuggle ')
#             pkg_name = pkg_name.replace('from ', '').strip()
#             if ' as ' in name:
#                 name, as_ = name.split(' as ')
#             else:
#                 as_ = name
#             name = name.strip('()\n\t ')
#             as_ = as_.strip()
#             full_name = f'{pkg_name}.{name}'
#             line = f'smuggle("{full_name}", as_="{as_}")'
#         else:
#             # standard smuggle call, e.g.:
#             #   `smuggle pandas as pd`
#             pkg_name = stripped.replace('smuggle ', '')
#             if ' as ' in pkg_name:
#                 pkg_name, as_ = pkg_name.split(' as ')
#                 # add quotes here so None can be passed without them
#                 as_ = f'"{as_.strip()}"'
#             else:
#                 as_ = None
#             pkg_name = pkg_name.strip('()\n\t ')
#             line = f'smuggle("{pkg_name}", as_={as_})'
#         # restore original indent
#         line = ' ' * indent_len + line
#     return line


smuggle_colab._register = register_smuggler_colab
