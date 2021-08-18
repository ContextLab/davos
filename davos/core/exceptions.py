"""
This module defines the set of `davos`-related exception classes.
"""


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
from shutil import get_terminal_size
from subprocess import CalledProcessError
from textwrap import fill, indent

import IPython


class DavosError(Exception):
    """Base class for all `davos` library exceptions."""


class DavosConfigError(DavosError):
    """Class for errors related to the `davos.config` object."""

    def __init__(self, field, msg):
        """
        Parameters
        ----------
        field : str
            The config field about which the exception should be raised
        msg : str
            The specific error message
        """
        self.field = field
        self.msg = msg
        super().__init__(f"'davos.config.{field}': {msg}")


class DavosParserError(SyntaxError, DavosError):
    """
    Base class for errors raised during the pre-execution parsing phase.

    Any `davos` exception classes related to user input-parsing step
    must inherit from this class in order to work in IPython
    environments.

    Notes
    -----
    Since the raw cell contents haven't been passed to the Python
    compiler yet, IPython doesn't allow input transformers to raise any
    exceptions other than `SyntaxError` during the input transformation
    phase.  All others will cause the cell to hang indefinitely, meaning
    all `davos` library exception classes related to the parsing phrase
    must inherit from `SyntaxError` in order to work.
    """

    def __init__(
            self,
            msg=None,
            target_text=None,
            target_offset=1
    ):
        """
        Parameters
        ----------
        msg : str, optional
            The error message to be displayed.
        target_text : str, optional
            The text of the code responsible for the error, to be
            displayed in Python's `SyntaxError`-specific traceback
            format. Typically, this is the full text of the line on
            which the error occurred, with whitespace stripped. If
            `None` (default), no text is shown and `target_offset` has
            no effect.
        target_offset : int, optional
            The (*1-indexed*) column offset from the beginning of
            `target_text` where the error occurred. Defaults to `1` (the
            first character in `target_text`).
        """
        # note: flot is a 4-tuple of (filename, lineno, offset, text)
        # passed to the SyntaxError constructor.
        if target_text is None or IPython.version_info[0] >= 7:
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
        super().__init__(msg, flot)


class OnionParserError(DavosParserError):
    """Class for errors related to parsing the onion comment syntax."""


class OnionArgumentError(ArgumentError, OnionParserError):
    """
    Class for errors related to arguments provided via an onion comment.

    This exception class inherits from both `OnionParserError` and
    `argparse.ArgumentError`. It functions as an onion comment-specific
    analog of `argparse.ArgumentError`, whose key distinction is that
    it can be raised during IPython's pre-execution phase (due to
    inheriting from `DavosParserError`). Instances of this exception can
    be expected to support attributes defined on both parents.
    """

    def __init__(self, msg, argument=None, onion_txt=None):
        """
        Parameters
        ----------
        msg : str
            The error message to be displayed.
        argument : str, optional
            The argument responsible for the error. if `None` (default),
            determines the argument name from `msg`, which will be the
            error message from an `argparse.ArgumentError` instance.
        onion_txt : str, optional
            The text of the installer arguments from onion comment in
            which the error occurred (i.e., the full onion comment with
            `# <installer>:` removed). If `None` (default), the error
            will not be displayed in Python's `SyntaxError`-specific
            traceback format.
        """
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
                                  target_offset=target_offset)
        self.argument_name = argument


class ParserNotImplementedError(OnionParserError, NotImplementedError):
    """
    Class for errors related to yet-to-be-implemented onion parsers.

    This exception is an onion comment-specific subclass of the built-in
    `NotImplementedError` that also inherits from `OnionParserError`,
    allowing it to be raised during IPython's pre-execution phase (due
    to inheriting from `DavosParserError`). This error is specifically
    raised when a user specifies an installer program (via an onion
    comment) whose command line parser has not yet been added to `davos`
    """


class SmugglerError(DavosError):
    """Base class for errors raised during the smuggle phase"""


class TheNightIsDarkAndFullOfTerrors(SmugglerError):
    """A little Easter egg for if someone tries to `smuggle davos`"""


class InstallerError(SmugglerError, CalledProcessError):
    """
    Class for errors related to the installer program

    This exception is raised when the installer program itself (rather
    than `davos`) encounters an error (e.g., failure to connect to
    upstream package repository, find package with a given name, resolve
    local environment, etc.).
    """

    @classmethod
    def from_error(cls, cpe, show_output=None):
        """
        Create a class instance from a `subprocess.CalledProcessError`

        Parameters
        ----------
        cpe : subprocess.CalledProcessError
            The exception from which to create the `InstallerError`
        show_output : bool, optional
            Whether or not to include the failed command's stdout and/or
            stderr in the error message. If `None` (default),
            stdout/stderr will be displayed if the `suppress_stdout`
            field of `davos.config` is currently set to `True` (i.e.,
            stdout would have been suppressed during execution).

        Returns
        -------
        InstallerError
            The exception instance.
        """
        if not isinstance(cpe, CalledProcessError):
            raise TypeError(
                "InstallerError.from_error() requires a "
                f"'subprocess.CalledProcessError' instance, not a {type(cpe)}"
            )
        return cls(returncode=cpe.returncode,
                   cmd=cpe.cmd,
                   output=cpe.output,
                   stderr=cpe.stderr,
                   show_output=show_output)

    def __init__(
            self,
            returncode,
            cmd,
            output=None,
            stderr=None,
            show_output=None
    ):
        """
        Parameters
        ----------
        returncode : int
            Return code for the failed command.
        cmd : str
            Text of the failed command.
        output : str, optional
            stdout generated from executing `cmd`.
        stderr : str, optional
            stderr generated from executing `cmd`.
        show_output : bool, optional
            Whether or not to include the failed command's stdout and/or
            stderr in the error message. If `None` (default),
            stdout/stderr will be displayed if the `suppress_stdout`
            field of `davos.config` is currently set to `True` (i.e.,
            stdout would have been suppressed during execution).
        """
        super().__init__(returncode=returncode, cmd=cmd, output=output,
                         stderr=stderr)
        if show_output is None:
            from davos import config
            # if stdout from installer command that raised error was
            # suppressed, include it in the error message
            self.show_output = config.suppress_stdout
        else:
            self.show_output = show_output

    def __str__(self):
        msg = super().__str__()
        if self.show_output and (self.output or self.stderr):
            msg = f"{msg} See below for details."
            textwidth = min(get_terminal_size().columns, 85)
            if self.output:
                text = fill(self.output, textwidth, replace_whitespace=False)
                msg = f"{msg}\n\nstdout:\n{indent(text, '    ')}"
            if self.stderr:
                text = fill(self.stderr, textwidth, replace_whitespace=False)
                msg = f"{msg}\n\nstderr:\n{indent(text, '    ')}"
        return msg
