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
import sys
from subprocess import CalledProcessError

from davos import davos
from davos.core import Onion, prompt_input, smuggle_statement_regex
from davos.exceptions import DavosParserError

if davos.ipython_shell is not None:
    from IPython.core.display import _display_mimetype
    from IPython.core.inputtransformer import StatelessInputTransformer
    from IPython.core.interactiveshell import system as _run_shell_cmd
    from IPython.utils.importstring import import_item
    # additional check to make sure this is in a Colab notebook rather
    # than just very old IPython kernel
    from ipykernel.zmqshell import ZMQInteractiveShell
    if type(davos.ipython_shell) is not ZMQInteractiveShell:
        from google.colab._pip import (
            _previously_imported_packages as get_updated_imported_pkgs
        )


def _showsyntaxerror_davos(colab_shell, filename=None):
    """
    METHOD UPDATED BY DAVOS PACKAGE

    When davos is imported into a Google Colab notebook, this method is
    bound to the IPython InteractiveShell instance in place of its
    normal `showsyntaxerror` method. This allows us to intercept
    handling of `DavosParserError` (which must derive from
    `SyntaxError`; see the `davos.exceptions.DavosParserError` docstring
    for more info) and its subclasses, and display parser exceptions
    properly with a full traceback.

    ORIGINAL
    `IPython.core.interactiveshell.InteractiveShell.showsyntaxerror`
    DOCSTRING:

    Display the syntax error that just occurred.

    This doesn't display a stack trace because there isn't one.

    If a filename is given, it is stuffed in the exception instead
    of what was there before (because Python's parser always uses
    "<string>" when reading from a string).
    """
    etype, value, tb = colab_shell._get_exc_info()
    if issubclass(etype, DavosParserError):
        try:
            # noinspection PyBroadException
            try:
                stb = value._render_traceback_()
            except:
                stb = colab_shell.InteractiveTB.structured_traceback(
                    etype, value, tb, tb_offset=colab_shell.InteractiveTB.tb_offset
                )
            colab_shell._showtraceback(etype, value, stb)
            if colab_shell.call_pdb:
                colab_shell.debugger(force=True)
            return
        except KeyboardInterrupt:
            print('\n' + colab_shell.get_exception_only(), file=sys.stderr)
    else:
        # original method is stored in Davos instance, but still bound
        # IPython.core.interactiveshell.InteractiveShell instance
        return davos._ipython_showsyntaxerror_orig(filename=filename)


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
    colab_shell.showsyntaxerror = _showsyntaxerror_davos.__get__(colab_shell)


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
            # Unlike regular import, can be called on non-module items:
            #     ```
            #     import numpy.array`                   # fails
            #     array = import_item('numpy.array')    # succeeds
            #     ```
            # Also adds module (+ parents, if any) to sys.modules if not
            # already present.
            smuggled_obj = import_item(name)
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
        # invalidate sys.meta_path module finder caches. Forces import
        # machinery to notice newly installed module
        importlib.invalidate_caches()
        # check whether the smuggled package and/or any installed/updated
        # dependencies were already imported during the current runtime
        prev_imported_pkgs = get_updated_imported_pkgs(installer_stdout)
        # if the smuggled package was previously imported, deal with
        # it last so it's reloaded after its dependencies are in place
        try:
            prev_imported_pkgs.remove(pkg_name)
        except ValueError:
            # smuggled package is brand new
            pass
        else:
            prev_imported_pkgs.append(pkg_name)

        failed_reloads = []
        for dep_name in prev_imported_pkgs:
            dep_modules_old = {}
            for mod_name in tuple(sys.modules.keys()):
                # remove submodules of previously imported packages so
                # new versions get imported when main package is
                # reloaded (importlib.reload only reloads top-level
                # module). IPython.lib.deepreload.reload recursively
                # reloads submodules, but is basically broken because
                # it's *too* aggressive. It reloads *all* imported
                # modules... including the import machinery it needs to
                # run, which crashes it... (-_-* )
                if mod_name.startswith(f'{dep_name}.'):
                    dep_modules_old[mod_name] = sys.modules.pop(mod_name)

            # get (but don't pop) top-level package to that it can be
            # reloaded (must exist in sys.modules)
            dep_modules_old[dep_name] = sys.modules[dep_name]
            try:
                importlib.reload(sys.modules[dep_name])
            except (ImportError, ModuleNotFoundError, RuntimeError):
                # if we aren't able to reload the module, put the old
                # version's submodules we removed back in sys.modules
                # for now and prepare to show a warning post-execution.
                # This way:
                #   1. the user still has a working module until they
                #      restart the runtime
                #   2. the error we got doesn't keep getting raised when
                #      we try to reload/import other modules that
                #      import it
                sys.modules.update(dep_modules_old)
                failed_reloads.append(dep_name)

        if any(failed_reloads):
            # packages with C extensions (e.g., numpy, pandas) cannot be
            # reloaded within an interpreter session. If the package was
            # previously imported in the current runtime (even if not by
            # user), warn about needing to reset runtime for changes to
            # take effect with "RESTART RUNTIME" button in output
            # (doesn't raise an exception, remaining code in cell still
            # runs)
            _display_mimetype(
                "application/vnd.colab-display-data+json",
                (
                    {'pip_warning': {'packages': ', '.join(failed_reloads)}},
                ),
                raw=True
            )
        smuggled_obj = import_item(name)
        # finally, reload pkg_resources so that just-installed package
        # will be recognized when querying local versions for later
        # checks
        importlib.reload(sys.modules['pkg_resources'])

    # add the object name/alias to the notebook's global namespace
    if as_ is None:
        davos.ipython_shell.user_ns[name] = smuggled_obj
    else:
        davos.ipython_shell.user_ns[as_] = smuggled_obj
    # cache the smuggled (top-level) package by its full onion comment
    # so rerunning cells is more efficient, but any change to version,
    # source, etc. is caught
    davos.smuggled[pkg_name] = onion.cache_key


def smuggle_parser_colab(line):
    # ADD DOCSTRING
    match = smuggle_statement_regex.match(line)
    if match is None:
        return line

    matched_groups = match.groupdict()
    smuggle_chars = matched_groups['FULL_CMD']
    before_chars, after_chars = line.split(smuggle_chars)
    cmd_prefix, to_smuggle = smuggle_chars.split('smuggle ', maxsplit=1)
    cmd_prefix = cmd_prefix.strip()
    to_smuggle = to_smuggle.strip()

    if cmd_prefix:
        # cmd_prefix == '"from" package[.module[...]] '
        is_from_statement = True
        onion_chars = matched_groups['FROM_ONION'] or matched_groups['FROM_ONION_1']
        has_semicolon_sep = matched_groups['FROM_SEMICOLON_SEP'] is not None
        qualname_prefix = f"{''.join(cmd_prefix.split()[1:])}."
        # remove parentheses around line continuations
        to_smuggle = to_smuggle.replace(')', '').replace('(', '')
        # remove inline comments
        if '\n' in to_smuggle:
            to_smuggle = ' '.join(l.split('#')[0] for l in to_smuggle.splitlines())
        else:
            to_smuggle = to_smuggle.split('#')[0]
        # normalize whitespace
        to_smuggle = ' '.join(to_smuggle.split()).strip(', ')
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
        onion_chars = onion_chars.replace('"', "'")
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
            name = f'"{qualname_prefix}{name}"'
            alias = f'"{alias.strip()}"'
        else:
            name = f'"{qualname_prefix}{na}"'
            alias = f'"{na.strip()}"' if is_from_statement else None

        name = name.replace(' ', '')
        smuggle_funcs.append(f'smuggle(name={name}, as_={alias})')

    smuggle_funcs[0] = smuggle_funcs[0][:-1] + kwargs_str + ')'
    return before_chars + '; '.join(smuggle_funcs) + after_chars
