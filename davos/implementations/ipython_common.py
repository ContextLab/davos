# ADD DOCSTRING


# TODO: fill me in
__all__ = []


import sys
from contextlib import redirect_stdout
from io import StringIO
from subprocess import CalledProcessError

from IPython.core.error import UsageError
from IPython.core.interactiveshell import system as _run_shell_cmd

from davos import config
from davos.core.exceptions import DavosParserError


def _run_shell_command_helper(command):
    # much simpler than plain Python equivalent because IPython has a
    # built-in utility function for running shell commands that handles
    # pretty much everything we need it to, and also formats outputs
    # nicely in the notebook
    retcode = _run_shell_cmd(command)
    if retcode != 0:
        raise CalledProcessError(returncode=retcode, cmd=command)
    return retcode


def _showsyntaxerror_davos(ipy_shell, filename=None, running_compiled_code=False):
    """
    When `davos` is imported into an IPython notebook, this method is 
    bound to the IPython InteractiveShell instance in place of its
    normal `showsyntaxerror` method. This allows `davos`` to intercept
    handling of `DavosParserError` (which must derive from
    `SyntaxError`; see the `davos.exceptions.DavosParserError` docstring
    for more info) and its subclasses, and display parser exceptions
    properly with complete tracebacks.
    
    The original wrapped method is is stored in 
    `davos.config._ipy_showsyntaxerror_orig`
    """
    etype, value, tb = ipy_shell._get_exc_info()
    if issubclass(etype, DavosParserError):
        try:
            # noinspection PyBroadException
            try:
                stb = value._render_traceback_()
            except:
                stb = ipy_shell.InteractiveTB.structured_traceback(
                    etype, value, tb, tb_offset=ipy_shell.InteractiveTB.tb_offset
                )
            ipy_shell._showtraceback(etype, value, stb)
            if ipy_shell.call_pdb:
                ipy_shell.debugger(force=True)
            return
        except KeyboardInterrupt:
            print('\n' + ipy_shell.get_exception_only(), file=sys.stderr)
    else:
        # original method is stored in Davos instance, but still bound
        # IPython.core.interactiveshell.InteractiveShell instance
        return config._ipy_showsyntaxerror_orig(filename=filename)
