# ADD DOCSTRING


# TODO: fill me in
__all__ = ['check_conda']


import textwrap
import sys
from contextlib import redirect_stdout
from io import StringIO
from subprocess import CalledProcessError

from IPython.core.error import UsageError
from IPython.core.interactiveshell import system as _run_shell_cmd

from davos import config
from davos.core.core import run_shell_command
from davos.core.exceptions import DavosError, DavosParserError


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


def check_conda():
    # ADD DOCSTRING
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
        config._conda_avail = False
        # config._conda_env & config._conda_envs_dirs are already None; 
        # no need to set those
    else:
        conda_list_output = conda_list_output.getvalue()
        config._conda_avail = True

        # try to create mapping of environment names to paths to 
        # validate environments used going forward. Want both names and 
        # paths so we can check both `-n`/`--name` & `-p`/`--prefix` 
        # when parsing onion comments
        envs_dict_command = "conda info --envs | grep -E '^\w' | sed -E 's/ +\*? +/ /g'"
        # noinspection PyBroadException
        try:
            conda_info_output = run_shell_command(envs_dict_command, 
                                                  live_stdout=False)
            # noinspection PyTypeChecker
            envs_dirs_dict = dict(map(str.split, conda_info_output.splitlines()))
        except Exception:
            # if no environments are found or output can't be parsed for 
            # some reason, just count any conda env provided as valid. 
            # This doesn't cause any major problems, we just can't catch 
            # errors as early and defer to the conda executable to throw 
            # an error when the user actually goes to install a package 
            # into an environment that doesn't exist
            # just set to None so it can be referenced down below
            envs_dirs_dict = None

        config._conda_envs_dirs = envs_dirs_dict
        # format of first line of output seems to reliably be:
        # `# packages in environment at /path/to/environment/dir:`
        # but can't hurt to parse more conservatively since output 
        # is so short
        for w in conda_list_output.split():
            if '/' in w:
                env_name = w.split('/')[-1].rstrip(':')
                if (
                        envs_dirs_dict is not None and 
                        env_name in envs_dirs_dict.keys()
                ):
                    config._conda_env = env_name
                    break
        else:
            if envs_dirs_dict is not None:
                # if we somehow fail to parse the environment directory 
                # path from the output, but we DID successfully create 
                # the environment mapping, something weird is going on, 
                # and it's worth throwing an error with some info now. 
                # Otherwise, defer potential errors to conda executable
                raise DavosError(
                    "Failed to programmatically determine path to conda "
                    "environment directory. If you want to install "
                    "smuggled packages using conda, you can either:\n\t1. set "
                    "`davos.config.conda_env_path` to your environment's path "
                    "(e.g., $CONDA_PREFIX/envs/this_env)\n\t2. pass the "
                    "environment path to `-p`/`--prefix` in each onion "
                    "comment\n\t3. pass your environment's name to  "
                    "`-n`/`--name` in each onion comment"
                )
