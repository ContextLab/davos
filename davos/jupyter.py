# ADD DOCSTRING


__all__ = [
    'activate_parser_jupyter',
    'check_parser_active_jupyter',
    'deactivate_parser_jupyter',
    'run_shell_command_jupyter',
    'smuggle_jupyter',
    'smuggle_parser_jupyter'
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
    

# TODO: TEMPORARY PLACEHOLDER FUNCTION UNTIL IMPLEMENTED
def get_updated_imported_pkgs(text):
    return []


def _showsyntaxerror_davos(ipython_shell, filename=None):
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
    etype, value, tb = ipython_shell._get_exc_info()
    if issubclass(etype, DavosParserError):
        try:
            # noinspection PyBroadException
            try:
                stb = value._render_traceback_()
            except:
                stb = ipython_shell.InteractiveTB.structured_traceback(
                    etype, value, tb, tb_offset=ipython_shell.InteractiveTB.tb_offset
                )
            ipython_shell._showtraceback(etype, value, stb)
            if ipython_shell.call_pdb:
                ipython_shell.debugger(force=True)
            return
        except KeyboardInterrupt:
            print('\n' + ipython_shell.get_exception_only(), file=sys.stderr)
    else:
        # original method is stored in Davos instance, but still bound
        # IPython.core.interactiveshell.InteractiveShell instance
        return davos._ipython_showsyntaxerror_orig(filename=filename)


def activate_parser_jupyter():
    # ADD DOCSTRING
    ipy_shell = davos.ipython_shell
    input_xforms = ipy_shell.input_transformers_post
    if smuggle_parser_jupyter not in input_xforms:
        input_xforms.append(smuggle_parser_jupyter)

    ipy_shell.user_ns['smuggle'] = smuggle_jupyter
    # ipy_shell.showsyntaxerror = _showsyntaxerror_davos.__get__(ipy_shell)


def check_parser_active_jupyter():
    # ADD DOCSTRING
    return smuggle_jupyter in davos.ipython_shell.input_transformers_post


def deactivate_parser_jupyter():
    # ADD DOCSTRING
    ipy_shell = davos.ipython_shell
    input_xforms = ipy_shell.input_transformers_post
    for xform in input_xforms:
        if xform is smuggle_parser_jupyter:
            input_xforms.remove(xform)
            break


def run_shell_command_jupyter(command):
    # much simpler than plain Python equivalent b/c IPython has a
    # built-in utility function for running shell commands that handles
    # pretty much everything we need it to, and also formats outputs
    # nicely in the notebook
    retcode = _run_shell_cmd(command)
    if retcode != 0:
        raise CalledProcessError(returncode=retcode, cmd=command)
    return retcode


def smuggle_jupyter(
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
            print(f'failed to reload {failed_reloads}')
            # TODO: IMPLEMENT THIS FOR JUPYTER NOTEBOOKS
            # _display_mimetype(
            #     "application/vnd.colab-display-data+json",
            #     (
            #         {'pip_warning': {'packages': ', '.join(failed_reloads)}},
            #     ),
            #     raw=True
            # )
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



def smuggle_parser_jupyter(line):
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
        after_chars = '; ' + smuggle_parser_jupyter(after_chars.lstrip('; '))
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


# IPython>=7.17: prevents transformer from being run when IPython is 
#  trying to guess whether user input is complete
# IPython<7.17: has no effect
smuggle_parser_jupyter.has_side_effects = True