"""
This module implements the 'smuggle' statement for interactive Python
environments built on top of IPython<7.0.0 (released 9/27/2018).

This implementation will most commonly be used in Google Colaboratory
notebooks (hence the module name), which as of 3/9/2021 run IPython
v5.5.0. However, IPython shells & Jupyter notebooks running older
versions of IPython will also use this approach
"""


__all__ = ['register_smuggler_colab', 'smuggle_colab']


import sys

from davos import config
from davos.core import Onion, prompt_input
from davos.exceptions import DavosParserError, OnionTypeError

if config.IPYTHON_SHELL is not None:
    from IPython.core.inputtransformer import StatelessInputTransformer
    from IPython.utils.importstring import import_item


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
    colab_shell = config.IPYTHON_SHELL
    smuggle_transformer = StatelessInputTransformer.wrap(smuggle_parser_colab)
    # entire IPython.core.inputsplitter module was deprecated in v7.0.0,
    # but Colab runs v5.5.0, so we still have to register our
    # transformer in both places for it to work correctly
    # noinspection PyDeprecation
    colab_shell.input_splitter.python_line_transforms.append(smuggle_transformer())
    colab_shell.input_transformer_manager.python_line_transforms.append(smuggle_transformer())
    colab_shell.user_ns['smuggle'] = smuggle_colab


def smuggle_colab(name, as_=None, **onion_kwargs):
    # ADD DOCSTRING
    # NOTE: 'name' can be a package, subpackage, module or object
    # TODO: what if name is a path to a local file or module?
    pkg_name = name.split('.')[0]
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
            if config.CONFIRM_INSTALL:
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
        onion.install_package()
        imported_obj = import_item(name)

    colab_shell = config.IPYTHON_SHELL
    if as_ is None:
        if name == pkg_name:
            colab_shell.user_ns[name] = sys.modules[name]
        else:
            colab_shell.user_ns[name] = imported_obj
    else:
        colab_shell.user_ns[as_] = imported_obj


def smuggle_parser_colab(line):
    # ADD DOCSTRING
    stripped = line.strip()
    if (
            'smuggle ' in line and
            # ignore commented-out lines
            not stripped.startswith('#') and
            # if smuggle is not the first word, it must be preceded by
            # a space. Helps handle weird edge cases, e.g.:
            #   `self.unrelated_attr_that_endswith_smuggle = 1`
            (stripped.startswith('smuggle ') or ' smuggle ' in stripped)
    ):
        indent_len = len(line) - len(line.lstrip(' '))
        # need to handle lines with comments separately, before checking
        # for characters (',', ';', etc.) in line so characters in
        # comments don't cause false-positive
        if '#' in stripped:
            # have to deal with the possibility of:
            #   ```
            #   smuggle (b, # b onion comment
            #            c, # c onion comment # non-onion comment
            #            d) # d onion comment # non-onion comment # etc
            #   ```
            # and also:
            #  ```
            #   smuggle (    # could even be an arbitrary comment here...
            #       b,       # b onion comment
            #   # ... and even comments between lines...
            #       c,       # c onion comment
            #       d        # d onion comment # non-onion comment # etc
            #   )            # ... or on an "empty" line
            #   ```
            # or even:
            #   ```
            #   smuggle (b,       # b onion comment
            #            c,       # c onion comment
            #            d)       # d onion comment # non-onion comment # etc
            #   ```
            # - only way this can happen is with parentheses & newlines,
            #   so we can use that as a queue
            # - on each line, all text before first # is real code
            # - can only have one onion comment per module imported, so
            # we can discount statements that don't start with 'smuggle'
            if all(c in stripped for c in '()\n'):
                if stripped.startswith('smuggle'):
                    sub_lines = []
                    for _line in stripped.splitlines():
                        code, sep, comment = _line.partition('#')
                        code = code.strip(', ')
                        if code.endswith('(') or code == '' or code == ')':
                            # - skip empty first lines, i.e. 'smuggle ('
                            # - skip lines with no code, just comments
                            # - skip empty last lines, i.e. ')'
                            continue
                        else:
                            _line = f"smuggle {code.strip('() ')} {sep} {comment}"
                            sub_lines.append(smuggle_parser_colab(_line))
                elif stripped.startswith('from '):
                    # can only have one onion comment per package, for
                    # multiline, import from a single package, it can go
                    # either on the first line (better) or the last line
                    # (also allowed).
                    # NOTE: if there is ANY comment on the first line,
                    #  even if it is not an onion notation, the last
                    #  line will not be looked at
                    _lines = stripped.splitlines()
                    code, _, comment = _lines[0].partition('#')
                    pkg_name = code.split()[1]
                    comment = comment.strip()
                    if comment == '':
                        comment = _lines[-1].partition('#')[2].strip()
                    if comment == '':
                        sep = ''
                    else:
                        sep = ' # '
                    sub_lines = []
                    _lines = stripped.split('smuggle (')[1].splitlines()
                    for _line in _lines:
                        _line = _line.split('#')[0].strip('), ')
                        for name in _line.split(','):
                            if name != '':
                                _cmd = f'from {pkg_name} smuggle {name}'
                                sub_lines.append(_cmd)
                    # add onion comment to first statement so package
                    # exists when the rest are run
                    sub_lines[0] = f'{sub_lines[0]}{sep}{comment}'
                    sub_lines = list(map(smuggle_parser_colab, sub_lines))
                else:
                    raise DavosParserError(
                        "failed to parse multiline smuggle statement"
                    )
                line = '; '.join(sub_lines)
            else:
                # otherwise, there's only one onion comment
                # TODO: a way to catch this, which is normally a SyntaxError:
                #   ```
                #   import a, \  # a onion comment
                #          b, \  # b onion comment
                #          c,    # c onion comment
                #   ```
                stripped, _, raw_onion = stripped.partition('#')
                stripped = stripped.strip()
                # currently in form: `smuggle(pack.age, as_=['<alias>'|None])`
                base_smuggle_call = smuggle_parser_colab(stripped)
                # drop any trailing non-onion comments
                raw_onion = raw_onion.partition('#')[0]
                # {param: value} kwargs dict for smuggle_colab()
                peeled_onion = Onion.parse_onion_syntax(raw_onion)
                kwargs_fmt = ', '.join('='.join(map(str, kv)) for kv in peeled_onion.items())
                # insert the kwargs before the closing parenthesis
                line = f"{base_smuggle_call[-1]}, {kwargs_fmt})"
        elif ';' in stripped:
            # handles semicolon-separated smuggle calls, e.g.:
            #   `smuggle os.path; from pathlib smuggle Path; smuggle re`
            # by running function on each call individually & re-joining
            line = '; '.join(map(smuggle_parser_colab, stripped.split(';')))
        elif ',' in stripped:
            # handles comma-separated list of packages/modules/functions
            # to smuggle
            if stripped.startswith('from '):
                # smuggling multiple names from same package, e.g.:
                #   `from os.path smuggle dirname, join as opj, realpath`
                # is transformed internally into multiple smuggle calls:
                #   `smuggle os.path.dirname as dirname; smuggle os....`
                from_cmd, names = stripped.split(' smuggle ')
                names = names.strip('()\n\t ').split(',')
                all_cmds = [f'{from_cmd} smuggle {name}' for name in names]
            else:
                # smuggling multiple packages at once, e.g.:
                #   `smuggle collections.abc as abc, json, os`
                # is transformed into multiple smuggle calls, e.g.:
                #   `smugle collections.abc as abc; smuggle json, sm...`
                names = stripped.replace('smuggle ', '').split(',')
                all_cmds = [f'smuggle {name}' for name in names]
            line = '; '.join(map(smuggle_parser_colab, all_cmds))
        elif stripped.startswith('from '):
            # handles smuggle calls in formats like, e.g.:
            #   `from os.path smuggle join as opj`
            # by transforming them into, e.g.:
            #   `smuggle os.path.join as opj
            # This grammar can sometimes fail with the builtin import
            # statement, e.g.:
            #   `import numpy.array as array` # -> ModuleNotFoundError
            # but IPython.utils.importstring.import_item always succeeds
            pkg_name, name = stripped.split(' smuggle ')
            pkg_name = pkg_name.replace('from ', '').strip()
            if ' as ' in name:
                name, as_ = name.split(' as ')
            else:
                as_ = name
            name = name.strip('()\n\t ')
            as_ = as_.strip()
            full_name = f'{pkg_name}.{name}'
            line = f'smuggle("{full_name}", as_="{as_}")'
        else:
            # standard smuggle call, e.g.:
            #   `smuggle pandas as pd`
            pkg_name = stripped.replace('smuggle ', '')
            if ' as ' in pkg_name:
                pkg_name, as_ = pkg_name.split(' as ')
                # add quotes here so None can be passed without them
                as_ = f"'{as_.strip()}'"
            else:
                as_ = None
            pkg_name = pkg_name.strip('()\n\t ')
            line = f"smuggle('{pkg_name}', as_={as_})"
        # restore original indent
        line = ' ' * indent_len + line
    return line



################################# OLD ##################################


# def smuggle_colab(pkg_name, as_=None):
#     # ADD DOCSTRING
#     # NOTE: pkg_name can be a package, subpackage, module or importable object
#     try:
#         imported_obj = import_item(pkg_name)
#     except ModuleNotFoundError as e:
#         if config.CONFIRM_INSTALL:
#             msg = (f"package {pkg_name} is not installed.  Do you want to "
#                    "install it?")
#             install_pkg = ask_yes_no(msg, default='n', interrupt='n')
#         else:
#             install_pkg = True
#         if install_pkg:
#             if config._CURR_INSTALL_NAME is None:
#                 install_name = pkg_name.split('.')[0]    # toplevel_pkg
#             else:
#                 install_name = config._CURR_INSTALL_NAME
#                 config._CURR_INSTALL_NAME = None
#             if config.SUPPRESS_STDOUT:
#                 stdout_stream = StringIO()
#             else:
#                 stdout_stream = sys.stdout
#             with redirect_stdout(stdout_stream):
#                 exit_code = run_shell_command(f'pip install {install_name}')
#             if exit_code != 0:
#                 if config.SUPPRESS_STDOUT:
#                     sys.stderr.write(stdout_stream.getvalue().strip())
#                 err_msg = (f"installing package '{pkg_name}' returned a "
#                            f"non-zero exit code: {exit_code}. See above output "
#                            "for details")
#                 raise InstallerError(err_msg) from e
#             else:
#                 imported_obj = import_item(pkg_name)
#         else:
#             raise e
#         # import_item takes care of adding package to sys.modules, along
#         # with its parents if it's a subpackage, but *doesn't* add the
#         # module name/alias to globals() like the normal import statement
#     finally:
#         # reset value set by pipname after successful import without install needed
#         config._CURR_INSTALL_NAME = None
#
#     colab_shell = config.IPYTHON_SHELL
#     if as_ is None:
#         if '.' in pkg_name:
#             toplevel_pkg = pkg_name.split('.')[0]
#             colab_shell.user_ns[toplevel_pkg] = sys.modules[toplevel_pkg]
#         else:
#             colab_shell.user_ns[pkg_name] = imported_obj
#     else:
#         colab_shell.user_ns[as_] = imported_obj



smuggle_colab._register = register_smuggler_colab
