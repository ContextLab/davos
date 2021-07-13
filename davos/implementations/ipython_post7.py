# ADD DOCSTRING


__all__ = ['generate_parser_func']


from IPython.core.inputtransformer import assemble_python_lines

from davos import config


def _activate_helper(smuggle_func, parser_func):
    # ADD DOCSTRING
    ipy_shell = config._ipython_shell
    input_xforms = ipy_shell.input_transformers_post
    if parser_func not in input_xforms:
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


def generate_parser_func(line_parser):
    # ADD DOCSTRING
    pyline_assembler = assemble_python_lines()

    def full_parser(lines):
        if 'smuggle ' not in ''.join(lines):
            # if cell contains no potential smuggle statements, don't
            # bother parsing line-by-line
            return lines

        parsed_lines = []
        curr_buff = []
        for ix, raw_line in enumerate(lines):
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
                # logical line contains multiple physical lines
                if parsed_line == python_line:
                    # if multiline statement is not a smuggle statement,
                    # don't combine physical lines in output
                    parsed_lines.extend(curr_buff)
                    # last line isn't in curr_buff, so add it separately
                    parsed_lines.append(raw_line)
                else:
                    # logical line is a multiline smuggle statement
                    parsed_lines.append(f'{parsed_line}\n')
                # reset partially accumulated lines
                curr_buff.clear()
            else:
                # logical line contains single physical line
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

    # prevents transformer from being run multiple times when
    # IPython parses partial line to determine whether input is
    # complete
    full_parser.has_side_effects = True
    return full_parser
