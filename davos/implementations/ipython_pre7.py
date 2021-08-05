"""
This modules contains implementations of helper functions specific to
versions of `IPython` before v7.0.0 (the oldest officially supported
version is v5.5.0).
"""


__all__ = ['generate_parser_func']


from IPython.core.inputtransformer import StatelessInputTransformer

from davos import config


def _activate_helper(smuggle_func, parser_func):
    """
    `IPython<7.0.0`-specific implementation of `_activate_helper`.

    Helper function called when setting `davos.config.active = True` or
    running `davos.activate()`. Wraps the the `davos` parser
    (`parser_func`) in an
    `IPython/core.inputtransformer.StatelessInputTransformer` instance
    and registers it as both an `IPython` input transformer *and* input
    splitter (in the `python_line_transforms` group) if it isn't one
    already. Injects `smuggle_func` into the `IPython` user namespace as
    `"smuggle"`.

    Parameters
    ----------
    smuggle_func : callable
        Function to be added to the `IPython` user namespace under the
        name "`smuggle`" (typically, `davos.core.core.smuggle`).
    parser_func : callable
        Function to be registered as an `IPython` input transformer
        and input splitter (for `IPython<7.0.0`, the return value of
        `davos.implementations.ipython_pre7.generate_parser_func()`).

    See Also
    --------
    davos.core.core.smuggle : The `smuggle` function.
    generate_parser_func : Function that creates the `davos` parser.
    IPython.core.inputtransformer.StatelessInputTransformer :
        Wrapper class for stateless input transformer functions.

    Notes
    -----
    1. `IPython<7.0.0` allows input transformer functions to hook into
       three different steps of the `IPython` parser during the
       pre-execution phase, and transform user input at various stages
       before it's sent to the Python parser. The `davos` parser runs as
       a "`python_line_transform`", which is the last group of
       transforms run on the raw input. By this stage, the `IPython`
       parser has reassembled groups of "*physical*" lines joined by
       both explicit (backslash-based) and implicit
       (parenthesis/bracket/brace/etc.-based) line continuations into
       full Python statements so the `davos` parser will receive
       multiline `smuggle` statements will be as a single unit.
    2. `IPython<7.0.0` requires that custom input transformers be
       added to both the `IPython` shell's `input_splitter` attribute
       and its `input_transformer_manager`. The former set of functions
       is run by `IPython` when checking whether or not the user input
       is complete (i.e., after pressing enter in the `IPython` shell,
       is the existing input a full statement, or part of a multiline
       statement/code block?). The latter is run when parsing complete
       blocks of user input that will be executed as Python code.
    """
    ipy_shell = config._ipython_shell
    smuggle_transformer = StatelessInputTransformer.wrap(parser_func)
    # noinspection PyDeprecation
    splitter_xforms = ipy_shell.input_splitter.python_line_transforms
    manager_xforms = ipy_shell.input_transformer_manager.python_line_transforms

    if not any(t.func is parser_func for t in splitter_xforms):
        splitter_xforms.append(smuggle_transformer())

    if not any(t.func is parser_func for t in manager_xforms):
        manager_xforms.append(smuggle_transformer())

    # insert "smuggle" into notebook namespace
    ipy_shell.user_ns['smuggle'] = smuggle_func


# noinspection PyDeprecation
def _deactivate_helper(smuggle_func, parser_func):
    """
    `IPython<7.0.0`-specific implementation of `_deactivate_helper`.

    Helper function called when setting `davos.config.active = False` or
    running `davos.deactivate()`. Removes the
    `IPython/core.inputtransformer.StatelessInputTransformer` instance
    whose `.func` is the `davos` parser (`parser_func`) from both the
    `.input_splitter` and `input_transformer_manager` attributes the
    `IPython` shell. Deletes the variable named "`smuggle`" from the
    `IPython` user namespace if it (a) exists and (b) holds a reference
    to `smuggle_func`, rather than some other value.

    Parameters
    ----------
    smuggle_func : callable
        Function expected to be the value of "`smuggle`" in the
        `IPython` user namespace. Used to confirm that variable should
        be deleted (typically, `davos.core.core.smuggle`).
    parser_func : callable
        Function that should be removed from the set of `IPython` input
        transformers (for `IPython<7.0.0`, `davos.core.core.parse_line`
        or the return value of
        `davos.implementations.ipython_pre7.generate_parser_func()`,
        which are equivalent).

    See Also
    --------
    davos.core.core.smuggle : The `smuggle` function.
    generate_parser_func : Function that creates the `davos` parser.

    Notes
    -----
    1. Any `smuggle` statements following a call to `davos.deactivate()`
       will result in `SyntaxError`s unless the parser is reactivated
       first.
    2. The `davos` parser adds minimal overhead to cell execution.
       However, deactivating it once it is no longer needed (i.e., after
       the last `smuggle` statement) may be useful when measuring
       precise runtimes (e.g. profiling code), as the amount of overhead
       added is a function of the number of lines rather than
       complexity.
    """
    ipy_shell = config._ipython_shell
    splitter_xforms = ipy_shell.input_splitter.python_line_transforms
    manager_xforms = ipy_shell.input_transformer_manager.python_line_transforms
    for xform in splitter_xforms:
        if xform.func is parser_func:
            splitter_xforms.remove(xform)
            break

    for xform in manager_xforms:
        if xform.func is parser_func:
            manager_xforms.remove(xform)
            break

    if ipy_shell.user_ns.get('smuggle') is smuggle_func:
        del ipy_shell.user_ns['smuggle']


def generate_parser_func(line_parser):
    """
    `IPython<7.0.0`-specific implementation of `generate_parser_func`.

    Given a function that parses a single line of code, returns the full
    `davos` parser to be wrapped in an
    `IPython.core.inputtransformer.StatelessInputTransformer` and
    registered as both an input transformer and input splitter.
    Unlike more recent versions, `IPython<7.0.0` expects transformer
    functions to accept a single (reassembled) line of input at a time,
    so the full parser is simply the single-line parser.

    Parameters
    ----------
    line_parser : callable
        Function that parses a single line of user code (typically,
        `davos.core.core.parse_line`).

    Returns
    -------
    callable
        The function passed to `line_parser`.
    """
    return line_parser
