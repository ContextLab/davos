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
from contextlib import redirect_stdout
from io import StringIO

from davos import config
from davos.core import nullcontext

if config.IPYTHON_SHELL is not None:
    from IPython.core.inputtransformer import StatelessInputTransformer
    from IPython.core.interactiveshell import system as _run_shell_cmd
    from IPython.utils.importstring import import_item
    from IPython.utils.io import ask_yes_no


def pipname_parser_colab(line):
    stripped = line.strip()
    if stripped.startswith('@pipname'):
        pipname = stripped.replace('@pipname(', '').strip().split()[0].strip('")\'')
        config.CURR_INSTALL_NAME = pipname
    else:
        return line


def run_shell_command(cmd_str):
    """
    simple helper that runs a string command in a bash shell
    and returns its exit code
    """
    return _run_shell_cmd(f"/bin/bash -c '{cmd_str}'")


# noinspection PyDeprecation
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
    pipname_transformer = StatelessInputTransformer.wrap(pipname_parser_colab)
    # entire IPython.core.inputsplitter module was deprecated in
    # v7.0.0, but Colab runs v5.5.0, so we still have to register
    # our transformer in both places for it to work correctly
    colab_shell.input_splitter.python_line_transforms.append(pipname_transformer())
    colab_shell.input_transformer_manager.python_line_transforms.append(pipname_transformer())

    colab_shell.input_splitter.python_line_transforms.append(smuggle_transformer())
    colab_shell.input_transformer_manager.python_line_transforms.append(smuggle_transformer())
    colab_shell.user_ns['smuggle'] = smuggle_colab


def smuggle_colab(pkg_name, as_=None):
    # ADD DOCSTRING
    # NOTE: pkg_name can be a package, subpackage, module or importable object
    # TODO: handle install for packages whose installable names are
    #  different form their importable names
    try:
        imported_obj = import_item(pkg_name)
    except ModuleNotFoundError as e:
        install_pkg = True
        if config.CONFIRM_INSTALL:
            msg = (f"package {pkg_name} is not installed.  Do you want to "
                   "install it?")
            install_pkg = ask_yes_no(msg, default='n', interrupt='n')
        if install_pkg:
            if config.CURR_INSTALL_NAME is None:
                install_name = pkg_name.split('.')[0]    # toplevel_pkg
            else:
                install_name = config.CURR_INSTALL_NAME
                config.CURR_INSTALL_NAME = None
            if config.SUPPRESS_STDOUT:
                stdout_stream = StringIO()
            else:
                stdout_stream = sys.stdout
            with redirect_stdout(stdout_stream):
                exit_code = run_shell_command(f'pip install {install_name}')
            if exit_code != 0:
                if config.SUPPRESS_STDOUT:
                    sys.stderr.write(stdout_stream.getvalue().strip())
                err_msg = (f"installing package '{pkg_name}' returned a "
                           f"non-zero exit code: {exit_code}. See above output "
                           "for details")
                raise ChildProcessError(err_msg) from e
            else:
                imported_obj = import_item(pkg_name)
        else:
            raise e
        # import_item takes care of adding package to sys.modules, along
        # with its parents if it's a subpackage, but *doesn't* add the
        # module name/alias to globals() like the normal import statement
    colab_shell = config.IPYTHON_SHELL
    if as_ is None:
        if '.' in pkg_name:
            toplevel_pkg = pkg_name.split('.')[0]
            colab_shell.user_ns[toplevel_pkg] = sys.modules[toplevel_pkg]
        else:
            colab_shell.user_ns[pkg_name] = imported_obj
    else:
        colab_shell.user_ns[as_] = imported_obj


def smuggle_parser_colab(line):
    stripped = line.strip()
    if (
            'smuggle ' in line and
            # ignore commented-out lines
            not stripped.startswith('#') and
            # if smuggle is not the first word, it must be preceded by
            # a space. Handles edge cases, e.g.:
            #   `self.unrelated_attr_that_endswith_smuggle = 1`
            (stripped.startswith('smuggle ') or ' smuggle ' in stripped)
        ):
        # note: shouldn't need to replace \t with spaces here
        indent_len = len(line) - len(line.lstrip(' '))
        if ';' in stripped:
            # handles semicolon-separated smuggle calls, e.g.:
            #   `smuggle os.path; from pathlib smuggle Path; smuggle re`
            # by running function on each call individually & re-joining
            line = '; '.join(map(smuggle_parser_colab, stripped.split(';')))
        elif ',' in stripped:
            # handles comma-separated list of packages/modules/functions
            # to smuggle
            if stripped.startswith('from '):
                # smuggling multiple names from same package, e.g.:
                #   `from os.path smuggle dirname, join as opj, relpath`
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
            line = f"smuggle('{full_name}', as_='{as_}')"
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


smuggle_colab._register_smuggler = register_smuggler_colab
