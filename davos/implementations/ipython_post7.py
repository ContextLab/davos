"""
This modules contains implementations of helper functions specific to
newer versions of `IPython`, starting with v7.0.0.
"""


__all__ = ['generate_parser_func']


from IPython.core.inputtransformer import assemble_python_lines

from davos import config


def _activate_helper(smuggle_func, parser_func):
    """
    `IPython>=7.0.0`-specific implementation of `_activate_helper`.

    Helper function called when setting `davos.config.active = True` or
    running `davos.activate()`. Registers the `davos` parser
    (`parser_func`) as an `IPython` input transformer (in the
    `input_transformers_post` group) if it isn't one already. Injects
    `smuggle_func` into the `IPython` user namespace as `"smuggle"`.

    Parameters
    ----------
    smuggle_func : callable
        Function to be added to the `IPython` user namespace under the
        name "`smuggle`" (typically, `davos.core.core.smuggle`).
    parser_func : callable
        Function to be registered as an `IPython` input transformer (for
        `IPython>=7.0.0`, the return value of
        `davos.implementations.ipython_post7.generate_parser_func()`).

    See Also
    --------
    davos.core.core.smuggle : The `smuggle` function.
    generate_parser_func : Function that creates the `davos` parser.
    """
    ipy_shell = config._ipython_shell
    input_xforms = ipy_shell.input_transformers_post
    if parser_func not in input_xforms:
        input_xforms.append(parser_func)

    # insert "smuggle" into notebook namespace
    ipy_shell.user_ns['smuggle'] = smuggle_func


def _deactivate_helper(smuggle_func, parser_func):
    """
    `IPython>=7.0.0`-specific implementation of `_deactivate_helper`.

    Helper function called when setting `davos.config.active = False` or
    running `davos.deactivate()`. Removes the `davos` parser
    (`parser_func`) from the set of `IPython` input transformers and
    deletes the variable named "`smuggle`" from the `IPython` user
    namespace if it (a) exists and (b) holds a reference to
    `smuggle_func`, rather than some other value.

    Parameters
    ----------
    smuggle_func : callable
        Function expected to be the value of "`smuggle`" in the
        `IPython` user namespace. Used to confirm that variable should
        be deleted (typically, `davos.core.core.smuggle`).
    parser_func : callable
        Function that should be removed from the set of `IPython` input
        transformers (for `IPython>=7.0.0`, the return value of
        `davos.implementations.ipython_post7.generate_parser_func()`).

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
    try:
        ipy_shell.input_transformers_post.remove(parser_func)
    except ValueError:
        pass

    if ipy_shell.user_ns.get('smuggle') is smuggle_func:
        del ipy_shell.user_ns['smuggle']


def generate_parser_func(line_parser):
    """
    `IPython>=7.0.0`-specific implementation of `generate_parser_func`.

    Given a function that parses a single line of code, returns the full
    `davos` parser to be registered as an `IPython` input transformer.

    Parameters
    ----------
    line_parser : callable
        Function that parses a single line of user code (typically,
        `davos.core.core.parse_line`).

    Returns
    -------
    callable
        The `davos` parser for use as an `IPython` input transformer.
        Given user input consisting of one or more lines (e.g., a
        notebook cell), returns the input with all lines parsed.

    See Also
    --------
    davos.core.core.parse_line : Single-line parser function.

    Notes
    -----
    1. In order to handle multiline `smuggle` statements, the
       `line_parser` function (`davos.core.core.parse_line`) works on
       "*logical*"/"*assembled*" lines, rather than "*physical*" lines.
       A logical line may consist of a single physical line, or multiple
       physical lines joined by explicit (i.e., backslash-based) or
       implicit (i.e., parenthesis/bracket/brace/etc.-based). For
       example, each of the following comprise multiple physical lines,
       but a single logical line:
       ```python
       from foo import bar \
                       baz \
                       qux \
                       quux

       spam = [ham,
               eggs,
               ni]

       the_night = {
           'dark': True,
           'full_of_terrors': True
       }
       ```
    2. The API for input transformations was completely overhauled in
       `IPython` v7.0. Among other changes, there is no longer a hook
       exposed for input transformers that work on fully assembled
       multiline statements (previously called
       `python_line_transforms`). Additionally, all input transformer
       functions are now called once per input area (i.e., notebook cell
       or interactive shell prompt) and are passed the full input,
       rather being called on each individual line. The `IPython>=7.0.0`
       implementation of the `davos` parser handles this by tokenizing
       the and assembling logical lines from the full input before
       passing each to the `line_parser` function. While this adds some
       additional overhead compared to the `IPython<7.0.0` `davos`
       parser, the difference is functionally de minimis, and in fact
       outweighed by the new parser's ability to skip parsing cells that
       don't contain `smuggle` statements altogether.
    3. Before it is returned, the full `davos` parser function is
       assigned an attribute "`has_side_effects`", which is set to
       `True`. In `IPython>=7.17`, this will prevent the parser from
       being run when `IPython` checks whether or not the user input is
       complete (i.e., after pressing enter in the `IPython` shell, is
       the existing input a full statement, or part of a multiline
       statement/code block?). In `IPython<7.17`, this will have no
       effect.
    """
    pyline_assembler = assemble_python_lines()

    def full_parser(lines):
        if 'smuggle ' not in ''.join(lines):
            # if cell contains no potential smuggle statements, don't
            # bother parsing line-by-line
            return lines

        parsed_lines = []
        curr_buff = []
        for raw_line in lines:
            # don't include trailing '\n'
            python_line = pyline_assembler.push(raw_line[:-1])
            if python_line is None:
                # currently accumulating multiline logical line
                curr_buff.append(raw_line)
                continue

            # pass single-line parser full logical lines -- may be
            # single physical line or fully accumulated multiline
            # statement
            parsed_line = line_parser(python_line)
            if curr_buff:
                # logical line consists of multiple physical lines
                if parsed_line == python_line:
                    # multiline statement is not a smuggle statement;
                    # don't combine physical lines in output
                    parsed_lines.extend(curr_buff)
                    # last line isn't in curr_buff; add it separately
                    parsed_lines.append(raw_line)
                else:
                    # logical line is a multiline smuggle statement
                    parsed_lines.append(f'{parsed_line}\n')
                # reset partially accumulated lines
                curr_buff.clear()
            else:
                # logical line consists of a single physical line
                parsed_lines.append(f'{parsed_line}\n')

        # .reset() clears pyline_assembler's .buf & .tokenizer for next
        # cell. Returns ''.join(pyline_assembler.buf) if .buf list is
        # not empty, otherwise None
        if pyline_assembler.reset():
            # Presence of an incomplete logical line after parsing the
            # last physical line means there's a SyntaxError somewhere.
            # Include remaining physical lines to let IPython/Python
            # deal with raising the SyntaxError from the proper location
            parsed_lines.extend(curr_buff)
        return parsed_lines

    # prevents transformer from being run multiple times when IPython
    # parses partial line to determine whether input is complete
    full_parser.has_side_effects = True
    return full_parser
