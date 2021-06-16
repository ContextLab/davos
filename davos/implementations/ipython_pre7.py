# ADD DOCSTRING


# TODO: add __all__


from IPython.core.inputtransformer import StatelessInputTransformer

from davos import config


def _activate_helper(smuggle_func, parser_func):
    """
    TODO: update docstring

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
    # TODO: update docstring

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
    # ADD DOCSTRING
    return line_parser
