# ADD DOCSTRING


# TODO: fill me in
__all__ = []


import textwrap
import sys
from contextlib import redirect_stdout
from io import StringIO
from subprocess import CalledProcessError

from IPython.core.error import UsageError
from IPython.core.interactiveshell import system as _run_shell_cmd

from davos import config
from davos.core.exceptions import DavosParserError


def _check_conda_avail_helper():
    """
    IPython implementation of helper function for 
    `davos.core.core.check_conda`. Checks whether conda executable is 
    available for use
    """
    try:
        with redirect_stdout(StringIO()) as conda_list_output:
            # this specific line magic seems to be the only reliable way 
            # to *actually* get the kernel environment -- shell (!) 
            # commands and all conda magic (%) commands other than 
            # `conda list` run in the base conda environment. Listed 
            # package is arbitrary, but listing single package is much 
            # faster than listing all, so using IPython because it's 
            # guaranteed to be installed
            config._ipython_shell.run_line_magic('conda', 'list IPython')
    except UsageError:
        # %conda line magic is not available
        return None
    return conda_list_output.getvalue()


def _run_shell_command_helper(command):
    # much simpler than plain Python equivalent because IPython has a
    # built-in utility function for running shell commands that handles
    # pretty much everything we need it to, and also formats outputs
    # nicely in the notebook
    retcode = _run_shell_cmd(command)
    if retcode != 0:
        raise CalledProcessError(returncode=retcode, cmd=command)


def _set_custom_showsyntaxerror():
    if config._ipy_showsyntaxerror_orig is not None:
        # function has already been called
        return
    # TODO: unless it causes circular import, raise DavosError elif 
    #  config.ipython_shell is None (i.e., function was called when 
    #  using pure Python implementation)

    ipy_shell = config.ipython_shell
    new_doc = textwrap.dedent(f"""\
        ===============================

        METHOD UPDATED BY DAVOS PACKAGE
        {_showsyntaxerror_davos.__doc__}
        ===============================

        ORIGINAL DOCSTRING:
        {config._ipy_showsyntaxerror_orig.__doc__}\
    """)

    _showsyntaxerror_davos.__doc__ = new_doc
    config._ipy_showsyntaxerror_orig = ipy_shell.showsyntaxerror
    ipy_shell.showsyntaxerror = _showsyntaxerror_davos.__get__(ipy_shell)


def _showsyntaxerror_davos(
        ipy_shell, 
        filename=None, 
        running_compiled_code=False
):
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
