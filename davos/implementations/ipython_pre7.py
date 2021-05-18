# ADD DOCSTRING


# TODO: add __all__


from IPython.core.inputtransformer import StatelessInputTransformer

from davos import config


def activate():
    # TODO: figure out a better way to organize this and deactivate() to 
    #  avoid local imports
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
    from davos.core.core import smuggle, smuggle_parser

    ipy_shell = config.ipython_shell
    smuggle_transformer = StatelessInputTransformer.wrap(smuggle_parser)
    # noinspection PyDeprecation
    splitter_xforms = ipy_shell.input_splitter.python_line_transforms
    manager_xforms = ipy_shell.input_transformer_manager.python_line_transforms
    if not any(t.func is smuggle_parser for t in splitter_xforms):
        splitter_xforms.append(smuggle_transformer())
    if not any(t.func is smuggle_parser for t in manager_xforms):
        manager_xforms.append(smuggle_transformer())

    ipy_shell.user_ns['smuggle'] = smuggle
