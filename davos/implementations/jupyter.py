# ADD DOCSTRING


__all__ = ['prompt_rerun_buttons']


import sys
import time
from textwrap import dedent

import ipykernel
import zmq
from IPython.display import display, Javascript
from ipython_genutils import py3compat

from davos.implementations.js_functions import JS_FUNCTIONS


def prompt_rerun_buttons():
    # ADD DOCSTRING
    # noinspection JSUnusedLocalSymbols,JSUnresolvedFunction
    button_args = dedent("""
        const buttonArgs = [
            {
                text: 'Restart Kernel and Rerun Cells',
                result: 'restart',
                onClick: () => {restartRunCellsAbove();},
            },
            {
                text: 'Continue Running',
                result: 'continue',
            },
        ]
    """)
    display_button_prompt_full = dedent(f"""
        {JS_FUNCTIONS.jupyter.restartRunCellsAbove};
        console.log('restartRunCellsAbove defined');
        
        {JS_FUNCTIONS.jupyter.displayButtonPrompt};
        console.log('displayButtonPrompt defined');
        
        {button_args};
        displayButtonPrompt(buttonArgs, true)
    """)

    # noinspection PyUnresolvedReferences
    # (function exists globally when imported into IPython context)
    kernel = get_ipython().kernel
    stdin_sock = kernel.stdin_socket

    # flush output before creating display
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
            else:
                raise

    # noinspection PyTypeChecker
    display(Javascript(display_button_prompt_full))

    while True:
        try:
            # zmq.select args:
            #   - sockets/FDs to be polled for read events
            #   - sockets/FDs to be polled for write events
            #   - sockets/FDs to be polled for error events
            #   - timeout (in seconds; None implies no timeout)
            # https://github.com/zeromq/pyzmq/blob/c02e8a1094be8d817020af221a283176ff22eed5/zmq/sugar/poll.py#L108
            # ('main' branch as of 7/21/2021)
            rlist, _, xlist = zmq.select([stdin_sock], [], [stdin_sock], 0.01)
            if rlist or xlist:
                ident, reply = kernel.session.recv(stdin_sock)
                if ident is not None or reply is not None:
                    break
        except KeyboardInterrupt:
            # re-raise KeyboardInterrupt with simplified traceback
            # (excludes some convoluted calls to internal IPython/zmq
            # machinery)
            raise KeyboardInterrupt("Interrupted by user") from None

    # noinspection PyBroadException
    try:
        value = py3compat.unicode_to_str(reply['content']['value'])
    except Exception:
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


def rerun_cells():
    # ADD DOCSTRING
    js_full = dedent(f"""
        {JS_FUNCTIONS.jupyter.restartRunCellsAbove};
        console.log('restartRunCellsAbove defined');
        
        restartRunCellsAbove();
    """)

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
