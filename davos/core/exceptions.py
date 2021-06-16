__all__ = [
    'DavosError',
    'DavosConfigError',
    'DavosParserError',
    'OnionParserError',
    'OnionArgumentError',
    'ParserNotImplementedError',
    'SmugglerError',
    'InstallerError'
]


from argparse import ArgumentError
from subprocess import CalledProcessError


class DavosError(Exception):
    pass


class DavosConfigError(DavosError):
    """general class for errors related to the Davos Config object"""
    def __init__(self, field, msg):
        # ADD DOCSTRING
        self.field = field
        self.msg = msg
        super().__init__(f"'davos.config.{field}': {msg}")


class DavosParserError(SyntaxError, DavosError):
    """
    Base class for errors raised during the parsing step.

    Since the raw cell contents haven't been passed to the Python
    compiler yet, IPython doesn't allow input transformers to raise any
    exceptions other than `SyntaxError` during the input transformation
    phase.  All others will cause the cell to hang indefinitely, meaning
    all `davos` library exception classes must inherit from
    `SyntaxError` in order to work.

    Additionally, when the IPython parser catches a `SyntaxError` raised
    by an input transformer, it displays it using a custom output
    formatting class in order to handle `SyntaxError`-specific traceback
    formatting (line number & position of the offending code, etc.). So
    since there's no way for the `davos` parser to get around that
    display format and show exceptions with their "normal" formatting,
    we may as well use those fields to provide some helpful info rather
    than just leaving them blank.
    """
    def __init__(
            self,
            msg=None,
            target_text=None,
            target_offset=0,
            *args
    ):
        # ADD DOCSTRING
        #  - `target_text` is text we're searching for which caused
        #     error
        #  - `target_offset` is additional offset from start of
        #    `target_text` for placing caret (allows us to use longer,
        #    more specific phrase for `target_text` when needed)
        #  - `flot` is a 4-tuple of (**f**ilename, **l**ineno,
        #    **o**ffset, **t**ext) passed to the SyntaxError
        #    constructor.

        # TODO: this may be a lot easier using sys.exc_info(),
        #  inspect.stack(), inspect.getframeinfo(), etc.
        if target_text is None:
            flot = (None, None, None, None)
        else:
            from davos import config
            xform_manager = config.ipython_shell.input_transformer_manager
            # number of "real" lines in the current cell before the
            # start of the current "chunk" (potentially multi-line
            # python statement) being parsed
            n_prev_lines = len(xform_manager.source.splitlines())
            all_cell_lines = xform_manager.source_raw.splitlines()
            # remaining cell lines starting with the beginning of the
            # current "chunk" (no way to isolate just the current chunk)
            rest_cell_lines = all_cell_lines[n_prev_lines:]
            for ix, line in enumerate(rest_cell_lines, start=1):
                if target_text in line:
                    lineno = n_prev_lines + ix
                    offset = line.index(target_text) + target_offset
                    break
            else:
                offset = None
                lineno = None
            # leave lineno as None so IPython will fill it in as
            # "<ipython-input-...>"
            flot = (None, lineno, offset, target_text)
        super().__init__(msg, flot, *args)


class OnionParserError(DavosParserError):
    """general class for errors related to the Onion structure/object"""
    pass


class OnionArgumentError(ArgumentError, OnionParserError):
    def __init__(self, msg=None, argument=None, onion_txt=None, *args):
        if (
                msg is not None and
                argument is None and
                msg.startswith('argument ')
        ):
            split_msg = msg.split()
            argument = split_msg[1].rstrip(':')
            msg = ' '.join(split_msg[2:])
        if (onion_txt is not None) and (argument is not None):
            # default sorting is alphabetical where '--a' comes before
            # '-a', so long option name will always be checked first,
            # which is what we want
            for aname in sorted(argument.split('/')):
                if aname in onion_txt:
                    target_offset = onion_txt.index(aname)
                    break
            else:
                target_offset = 0
        else:
            target_offset = 0
        # both `argparse.ArgumentError` and `SyntaxError` are
        # non-cooperative, so need to initialize them separately rather
        # than just running through the MRO via a call to super()
        ArgumentError.__init__(self, argument=None, message=msg)
        OnionParserError.__init__(self, msg=msg, target_text=onion_txt,
                                  target_offset=target_offset, *args)
        self.argument_name = argument


class ParserNotImplementedError(OnionParserError, NotImplementedError):
    """
    A version of NotImplementedError that can be raised during IPython
    input transformation step because it inherits from SyntaxError
    """
    pass


class SmugglerError(DavosError):
    """class for errors raised during the smuggle step"""
    pass


class InstallerError(SmugglerError, CalledProcessError):
    """
    class for problems encountered by the installer (pip/conda) itself
    (e.g., failed to connect to internet, resolve environment, find
    package with given name, etc.)
    """
    def __init__(self, msg, *args, output=None, stderr=None,
                 show_stdout=None):
        cpe_or_retcode = args[0]
        if isinstance(cpe_or_retcode, CalledProcessError):
            returncode = cpe_or_retcode.returncode
            cmd = cpe_or_retcode.cmd
            output = output or cpe_or_retcode.output
            stderr = stderr or cpe_or_retcode.stderr
        else:
            try:
                returncode, cmd = args
            except ValueError:
                # TODO: raise this from the line of the constructor's
                #  signature
                raise TypeError(
                    "InstallerError requires, at minimum, either a "
                    "'subprocess.CalledProcessError' object or a return code "
                    "[int] and cmd [str]"
                ) from None
        super().__init__(returncode=returncode, cmd=cmd, output=output,
                         stderr=stderr)
        self.msg = msg
        if show_stdout is None:
            from davos import config
            if config.suppress_stdout and output is not None:
                show_stdout = True
            else:
                show_stdout = False
        if show_stdout:
            # TODO: change this so the command's stdout is inserted as
            #  a FrameSummary object in the stack trace at the line
            #  where davos.run_shell_command was called
            self.args = (*self.args, output)

    def __str__(self):
        return self.msg + '\n\t' + super().__str__()
