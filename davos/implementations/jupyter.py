"""
This modules contains implementations of helper functions specific to
Jupyter notebooks.
"""


__all__ = ['auto_restart_rerun', 'prompt_restart_rerun_buttons']


import sys
import time
from textwrap import dedent

import ipykernel
import zmq
from IPython.display import display, Javascript

from davos import config
from davos.implementations.js_functions import JS_FUNCTIONS


def auto_restart_rerun(pkgs):
    """
    Jupyter-specific implementation of `auto_restart_rerun`.

    Automatically restarts the notebook kernel and reruns all cells
    above, *including the current cell*. Called when one or more
    smuggled `pkgs` that were previously imported cannot be reloaded by
    the current interpreter, and `davos.config.auto_rerun` is set to
    `True`. Displays a message in the cell output area with the
    package(s) that required the kernel restart, calls
    `JS_FUNCTIONS.jupyter.restartRunCellsAbove`, and then blocks until
    the kernel is restarted.

    Parameters
    ----------
    pkgs : list of str
        Packages that could not be reloaded without restarting the
        kernel.

    See Also
    --------
    JS_FUNCTIONS.jupyter.restartRunCellsAbove :
        JavaScript function that restarts kernel and reruns cells above

    Notes
    -----
    1. The message displayed before restarting the kernel can be
       silenced by setting `davos.config.suppress_stdout` to `True`.
    2. After calling `JS_FUNCTIONS.jupyter.restartRunCellsAbove`, this
       function sleeps until until the kernel restarts to prevent any
       further code in the current cell or other queued cells from
       executing. Restarting the kernel is often not instantaneous;
       there's generally a 1-2s delay while the kernel sends & receives
       various shutdown messages, but it can take significantly
       longer on a slow machine, with older Python/Jupyter/ipykernel
       versions, if a large amount of data was loaded into memory, if
       multiple notebook kernels are running at once, etc. If this
       function returned immediately, it's likely subsequent lines of
       code would be run before the kernel disconnected. This can cause
       problems if those lines of code use the package(s) that prompted
       the restart, or have effects that persist across kernel sessions.
    """
    msg = (
        "Restarting kernel and rerunning cells (required to smuggle "
        f"{', '.join(pkgs)})..."
    )

    js_full = dedent(f"""
        {JS_FUNCTIONS.jupyter.restartRunCellsAbove};
        console.log('restartRunCellsAbove defined');

        console.log(`{msg}`);
        restartRunCellsAbove();
    """)

    if not config.suppress_stdout:
        print(f"\033[0;31;1m{msg}\033[0m")

    # flush output before creating display
    sys.stdout.flush()
    sys.stderr.flush()

    # noinspection PyTypeChecker
    display(Javascript(js_full))
    # block execution for clarity -- kernel restart can sometimes take a
    # few seconds to trigger, so prevent any queued code from running in
    # the interim in case it has effects that persist across kernel
    # sessions
    while True:
        time.sleep(10)


def prompt_restart_rerun_buttons(pkgs):
    """
    Jupyter-specific implementation of `prompt_restart_rerun_buttons`.

    Displays a warning that the notebook kernel must be restarted in
    order to use the just-smuggled version of one or more previously
    imported `pkgs`, and displays a pair of buttons (via
    `JS_FUNCTIONS.jupyter.displayButtonPrompt`) that prompt the user to
    either (a) restart the kernel and rerun all cells up to the current
    point, or (b) ignore the warning and continue running. Then, polls
    the kernel's stdin socket until it receives a reply from the
    notebook frontend, or the kernel is restarted.

    Parameters
    ----------
    pkgs : list of str
        Packages that could not be reloaded without restarting the
        kernel.

    Returns
    -------
    None
        If the user clicks the "Continue Running" button, returns
        `None`. Otherwise, restarts the kernel and therefore never
        returns.

    See Also
    --------
    JS_FUNCTIONS.jupyter.displayButtonPrompt :
        JavaScript function for prompting user input with buttons.
    ipykernel.kernelbase.Kernel._input_request :
        Kernel method that replaces the built-in `input` in notebooks.

    Notes
    -----
    1. This method of blocking and waiting for user input is based on
       `ipykernel`'s replacement for the built-in `input` function used
       in notebook environments.

    """
    # UI: could remove warning message when "continue" button is clicked
    msg = (
        "WARNING: The following packages were previously imported by the "
        "interpreter and could not be reloaded because their compiled modules "
        f"have changed:\n\t[{', '.join(pkgs)}]\nRestart the kernel to use "
        "the newly installed version."
    )

    # noinspection JSUnusedLocalSymbols,JSUnresolvedFunction
    button_args = dedent("""
        const buttonArgs = [
            {
                text: 'Restart Kernel and Rerun Cells',
                onClick: () => {restartRunCellsAbove();},
            },
            {
                text: 'Continue Running',
                result: null,
            },
        ]
    """)
    display_button_prompt_full = dedent(f"""
        {JS_FUNCTIONS.jupyter.restartRunCellsAbove};
        console.log('restartRunCellsAbove defined');
        
        {JS_FUNCTIONS.jupyter.displayButtonPrompt};
        console.log('displayButtonPrompt defined');
        
        {button_args};
        console.warn(`{msg}`);
        displayButtonPrompt(buttonArgs, true);
    """)

    # get_ipython() exists globally when imported into IPython context
    kernel = get_ipython().kernel
    stdin_sock = kernel.stdin_socket

    print(f"\033[0;31;1m{msg}\033[0m")

    # flush output before creating button display
    sys.stdout.flush()
    sys.stderr.flush()

    # flush ipykernel stdin socket to purge stale replies
    while True:
        try:
            # noinspection PyUnresolvedReferences
            # (dynamically imported names not included in stub files)
            stdin_sock.recv_multipart(zmq.NOBLOCK)
        except zmq.ZMQError as e:
            # noinspection PyUnresolvedReferences
            # (dynamically imported names not included in stub files)
            if e.errno == zmq.EAGAIN:
                break
            raise

    # noinspection PyTypeChecker
    display(Javascript(display_button_prompt_full))

    while True:
        try:
            # zmq.select (zmq.sugar.poll.select) args:
            #   - list of sockets/FDs to be polled for read events
            #   - list of sockets/FDs to be polled for write events
            #   - list of sockets/FDs to be polled for error events
            #   - timeout (in seconds; None implies no timeout)
            rlist, _, xlist = zmq.select([stdin_sock], [], [stdin_sock], 0.01)
            if rlist or xlist:
                ident, reply = kernel.session.recv(stdin_sock)
                if ident is not None or reply is not None:
                    break
        except Exception as e:    # pylint: disable=broad-except
            if isinstance(e, KeyboardInterrupt):
                # re-raise KeyboardInterrupt with simplified traceback
                # (excludes some convoluted calls to internal
                # IPython/zmq machinery)
                raise KeyboardInterrupt("Interrupted by user") from None
            kernel.log.warning("Invalid Message:", exc_info=True)

    # noinspection PyBroadException
    try:
        value = reply['content']['value']
    except Exception:    # pylint: disable=broad-except
        if ipykernel.version_info[0] >= 6:
            _parent_header = kernel._parent_ident['shell']
        else:
            _parent_header = kernel._parent_ident
        kernel.log.error(f"Bad input_reply: {_parent_header}")
        value = ''

    if value == '\x04':
        # end of transmission
        raise EOFError
    return value
