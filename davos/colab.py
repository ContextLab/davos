"""
This module implements the 'smuggle' statement for interactive Python
environments built on top of IPython<7.0.0 (released 9/27/2018).

This implementation will most commonly be used in Google Colaboratory
notebooks (hence the module name), which as of 3/9/2021 run IPython
v5.5.0. However, IPython shells & Jupyter notebooks running older
versions of IPython will also use this approach
"""


__all__ = [
    'activate_parser_colab',
    'check_parser_active_colab',
    'deactivate_parser_colab',
    'run_shell_command_colab',
    'smuggle_colab',
    'smuggle_parser_colab'
]


import importlib
import re
import sys
import warnings
from subprocess import CalledProcessError

from davos import davos
from davos.core import Onion, prompt_input, smuggle_statement_regex

if davos.ipython_shell is not None:
    from IPython.core.display import _display_mimetype
    from IPython.core.inputtransformer import StatelessInputTransformer
    from IPython.core.interactiveshell import system as _run_shell_cmd
    from IPython.lib.deepreload import reload as deep_reload
    from IPython.utils.importstring import import_item
    # additional check to make sure this is in a Colab notebook rather
    # than just very old IPython kernel
    from ipykernel.zmqshell import ZMQInteractiveShell
    if type(davos.ipython_shell) is not ZMQInteractiveShell:
        # noinspection PyUnresolvedReferences
        from google.colab._pip import (
            _previously_imported_packages as get_updated_imported_pkgs
        )


NO_RELOAD_MODULES = (
    'sys',
    'os.path',
    'builtins',
    '__main__',
    'numpy',
    'numpy._globals',
    'davos',
    'importlib',
    'types',
    *sys.builtin_module_names
)


def activate_parser_colab():
    """
    **Available in public API via `davos.activate()`**

    Registers the `davos` parser as an IPython `InputTransformer` that
    will be called on the contents of each code cell.  Can be run
    manually (`davos.activate()`) after deactivating parser
    (`davos.deactivate()`) to re-enable the `davos` parser for all
    future cells (**including the current cell**).

    Notes
    -----
    1. There are multiple groups of `InputTransformer`s that IPython
       runs on cell content at different pre-execution stages, between
       various steps of the IPython parser.  The `davos` parser is added
       as a "python_line_transform", which runs after the last step of
       the IPython parser, before the code is passed off to the Python
       parser. At this point, the IPython parser has reassembled both
       explicit (backslash-based) and implicit (parentheses-based) line
       continuations, so the parser will receive multi-line `smuggle`
       statements as a single line
    2. The entire `IPython.core.inputsplitter` module was deprecated in
       v7.0.0, but Colab runs v5.5.0, so the input transformer still
       needs to be registered in both places for it to work correctly
    """
    colab_shell = davos.ipython_shell
    smuggle_transformer = StatelessInputTransformer.wrap(smuggle_parser_colab)
    # noinspection PyDeprecation
    splitter_xforms = colab_shell.input_splitter.python_line_transforms
    manager_xforms = colab_shell.input_transformer_manager.python_line_transforms
    if not any(t.func is smuggle_parser_colab for t in splitter_xforms):
        splitter_xforms.append(smuggle_transformer())
    if not any(t.func is smuggle_parser_colab for t in manager_xforms):
        manager_xforms.append(smuggle_transformer())

    colab_shell.user_ns['smuggle'] = smuggle_colab


def check_parser_active_colab():
    # ADD DOCSTRING
    colab_shell = davos.ipython_shell
    # noinspection PyDeprecation
    splitter_xforms = colab_shell.input_splitter.python_line_transforms
    manager_xforms = colab_shell.input_transformer_manager.python_line_transforms
    if (
            any(t.func is smuggle_parser_colab for t in splitter_xforms) and
            any(t.func is smuggle_parser_colab for t in manager_xforms)
    ):
        return True
    return False


# noinspection PyDeprecation
def deactivate_parser_colab():
    """
    **Available in public API via `davos.deactivate()`**

    Disables the `davos` parser for all future cells (**including the
    current cell**).  The parser may be re-enabled by calling
    `davos.activate()`.

    Notes
    -----
    1. Any `smuggle` statements following a call to `davos.deactivate()`
       will result in `SyntaxError`s unless the parser is reactivated
       first.
    2. The `davos` parser adds very minimal overhead to cell execution.
       However, running `davos.deactivate()` once the parser is no
       longer needed (i.e., after the last `smuggle` statement) may be
       useful when measuring precise runtimes (e.g. profiling code),
       particularly because the overhead added is a function of the
       number of lines rather than complexity.
    *See notes for `activate_parser_colab()`*
    """
    colab_shell = davos.ipython_shell
    splitter_xforms = colab_shell.input_splitter.python_line_transforms
    manager_xforms = colab_shell.input_transformer_manager.python_line_transforms
    for xform in splitter_xforms:
        if xform.func is smuggle_parser_colab:
            splitter_xforms.remove(xform)
            break
    for xform in manager_xforms:
        if xform.func is smuggle_parser_colab:
            manager_xforms.remove(xform)
            break


def run_shell_command_colab(command):
    # much simpler than plain Python equivalent b/c IPython has a
    # built-in utility function for running shell commands that handles
    # pretty much everything we need it to, and also formats outputs
    # nicely in the notebook
    retcode = _run_shell_cmd(command)
    if retcode != 0:
        raise CalledProcessError(returncode=retcode, cmd=command)
    return retcode


def smuggle_colab(
        name,
        as_=None,
        installer='pip',
        args_str='',
        installer_kwargs=None
):
    # ADD DOCSTRING
    if installer_kwargs is None:
        installer_kwargs = {}

    pkg_name = name.split('.')[0]
    onion = Onion(pkg_name, installer=installer,
                  args_str=args_str, **installer_kwargs)

    if onion.is_installed:
        try:
            imported_obj = import_item(name)
        except ModuleNotFoundError as e:
            # TODO: check for --yes (conda) and bypass if passed
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
        # remove package and all of its subpackages from sys.modules
        for name in tuple(sys.modules.keys()):
            if name.startswith(f'{pkg_name}.') or name == pkg_name:
                del sys.modules[name]
        # invalidate sys.meta_path module finder caches. Forces import
        # machinery to notice newly installed module
        importlib.invalidate_caches()
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
            deep_reload(sys.modules[pkg_name], exclude=NO_RELOAD_MODULES)
        if check_smuggled_pkg:
            old_pkg = sys.modules[pkg_name]
            try:
                old_version = old_pkg.__version__
            except AttributeError:
                old_version = None
            new_pkg = deep_reload(old_pkg, exclude=NO_RELOAD_MODULES)
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
                elif onion.version_spec != '':
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
    davos.smuggled[onion.import_name] = onion.args_str


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
        qualname_prefix = cmd_prefix.split()[1] + '.'
        to_smuggle = re.sub(r'[()]|\s*\#.*$\s*', ' ', to_smuggle, flags=re.M)
        to_smuggle = to_smuggle.rstrip(', ')
    else:
        # cmd_prefix == ''
        is_from_statement = False
        onion_chars = matched_groups['ONION']
        has_semicolon_sep = matched_groups['SEMICOLON_SEP'] is not None
        qualname_prefix = ''

    kwargs_str = ''
    if has_semicolon_sep:
        after_chars = '; ' + smuggle_parser_colab(after_chars.lstrip('; '))
    elif onion_chars is not None:
        to_smuggle = to_smuggle.replace(onion_chars, '').rstrip()
        # `Onion.parse_onion()` returns a 3-tuple of:
        #  - the installer name (str)
        #  - the raw arguments to be passed to the installer (str)
        #  - an {arg: value} mapping from parsed args & defaults (dict)
        installer, args_str, installer_kwargs = Onion.parse_onion(onion_chars)
        kwargs_str = (f', installer={installer}, '
                      f'args_str={args_str}, '
                      f'installer_kwargs={installer_kwargs}')

    smuggle_funcs = []
    names_aliases = to_smuggle.split(',')
    for na in names_aliases:
        if ' as ' in na:
            name, alias = na.split(' as ')
            name = f'"{qualname_prefix}{name.strip()}"'
            alias = f'"{alias.strip()}"'
        else:
            na = na.strip()
            name = f'"{qualname_prefix}{na}"'
            alias = f'"{na}"' if is_from_statement else None

        smuggle_funcs.append(f'smuggle(name={name}, as_={alias})')

    smuggle_funcs[0] = smuggle_funcs[0][:-1] + kwargs_str + ')'
    return before_chars + '; '.join(smuggle_funcs) + after_chars
