# ADD DOCSTRING


# TODO: add __all__


from davos import config


def _activate_helper(smuggle_func, parser_func):
    # ADD DOCSTRING
    ipy_shell = config._ipython_shell
    input_xforms = ipy_shell.input_transformers_post
    if parser_func not in input_xforms:
        # prevents transformer from being run multiple times when 
        # IPython parses partial line to determine whether input is 
        # complete
        parser_func.has_side_effects = True
        input_xforms.append(parser_func)

    # insert "smuggle" into notebook namespace
    ipy_shell.user_ns['smuggle'] = smuggle_func


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
    try:
        ipy_shell.input_transformers_post.remove(parser_func)
    except ValueError:
        pass

    if ipy_shell.user_ns.get('smuggle') is smuggle_func:
        del ipy_shell.user_ns['smuggle']
