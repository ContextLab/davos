"""
This module defines reimplementations of the command line parsers for
installer programs supported by `davos`, slightly modified to parse
arguments supplied via an Onion comment.
"""


__all__ = ['EditableAction', 'OnionParser', 'pip_parser', 'SubtractAction']


import sys
from argparse import (
    Action,
    ArgumentError,
    ArgumentTypeError,
    ArgumentParser,
    SUPPRESS
)
from textwrap import dedent, indent

from davos.core.exceptions import OnionArgumentError


class OnionParser(ArgumentParser):
    """
    `argparse.ArgumentParser` subclass for parsing Onion comments.

    This class is essentially used to reimplement the installer
    programs' existing command line parsers with some slight tweaks
    specific to parsing Onion comments during the notebook's pre-cell
    execution phase. Since the arguments are eventually passed to the
    actual installer's parser, this is, admittedly, slightly redundant.
    However, it affords a number of advantages, such as:
        - protecting against shell injections (e.g., `# pip: --upgrade
          numpy && rm -rf /` fails due to the OnionParser, but would
          otherwise execute successfully)
        - detecting errors quickly, before spawning a subprocesses
        - allowing `davos` to adopt per-smuggle-command behaviors based
          on user-provided arguments (e.g., `--force-reinstall`,
          `-I/--ignore-installed`, `--no-input`, `-v/--verbose`, etc.)

    See Also
    --------
    argparse.ArgumentParser :
        https://docs.python.org/3/library/argparse.html#argumentparser-objects

    Notes
    -----
    Currently supported arguments are based on `pip` v21.1.3, regardless
    of the user's local `pip` version. However, the vast majority of
    arguments are consistent across versions.
    """

    # pylint: disable=signature-differs
    def parse_args(self, args, namespace=None):
        """
        Parse installer options as command line arguments.

        Parameters
        ----------
        args : list of str
            Command line arguments for the installer program specified
            in an Onion comment, split into a list of strings.
        namespace : object, optional
            An object whose namespace should be populated with the
            parsed arguments. If `None` (default), creates a new, empty
            `argparse.Namespace` object.

        Returns
        -------
        object
            The populated object passed as `namespace`
        """
        # pylint: disable=attribute-defined-outside-init
        self._args = ' '.join(args)
        try:
            ns, extras = super().parse_known_args(args=args,
                                                  namespace=namespace)
        except (ArgumentError, ArgumentTypeError) as e:
            if isinstance(e, OnionArgumentError):
                raise
            if isinstance(e, ArgumentError):
                raise OnionArgumentError(msg=e.message,
                                         argument=e.argument_name,
                                         onion_txt=self._args) from None
            raise OnionArgumentError(msg=e.args[0],
                                     onion_txt=self._args) from None
        else:
            if extras:
                msg = f"Unrecognized arguments: {' '.join(extras)}"
                raise OnionArgumentError(msg=msg,
                                         argument=extras[0],
                                         onion_txt=self._args)
            return ns
        finally:
            # noinspection PyAttributeOutsideInit
            self._args = None

    def error(self, message):
        """
        Raise an OnionArgumentError with a given message.

        This is needed to override `argparse.ArgumentParser.error()`.
        `argparse` is  which exits the program when called (in response
        to an exception being raised) because it is generally intended
        for command line interfaces. The generally idea is to affect the
        stack trace displayed for the user as little as possible, while
        also ensuring all exceptions raised inherit from `SyntaxError`
        so they can be successfully raised during the notebook cell
        pre-execution step.

        Parameters
        ----------
        message : str
            The error message to be displayed for the raised exception.
        """
        if sys.exc_info()[1] is not None:
            raise    # pylint: disable=misplaced-bare-raise
        if message == 'one of the arguments -e/--editable is required':
            message = 'Onion comment must specify a package name'
        raise OnionArgumentError(msg=message, onion_txt=self._args)


class EditableAction(Action):
    """
    `argparse.Action` subclass for pip's `-e/--editable <path/url>` arg.

    The `-e/--editable` argument is implemented in a slightly unusual
    way in order to allow the OnionParser to mimic the behavior of the
    real `pip install` command's far more complex parser. The argument
    is optional (default: `False`), and is mutually exclusive with the
    positional `spec` argument. If provided, it accepts/requires a
    single value (metavar: `'<path/url>'`). However, rather than storing
    the value in the `argparse.Namespace` object's "editable" attribute,
    the EditableAction stores `editable=True` and assigns the passed
    value to "`spec`". This way:
        1. As with the real `pip install` command, the project path/url
           for an editable install must immediately follow the
           `-e/--editable` argument (i.e., `/some/file/path -e` is
           invalid)
        2. The parser accepts only a single regular or editable package
           spec (since an Onion comment can only ever refer to a single
           package).
        3. After parsing, argument values and types are consistent and
           easier to handle: `spec` will always be the package spec and
           `editable` will always be a `bool`.
    """

    # noinspection PyShadowingBuiltins
    def __init__(
            self,
            option_strings,
            dest,
            default=None,
            metavar=None,
            help=None
    ):
        """
        Parameters
        ----------
        option_strings : sequence of str
            Command line option strings which should be associated with
            this action.
        dest : str
            The name of the attribute to hold the created object(s).
        default : multiple types, optional
            The value to be produced if the option is not specified
            (default: `None`).
        metavar : str, optional
            The name to be used for the option's argument with the help
            string. If `None` (default), the `dest` value will be used
            as the name.
        help : str, optional
            The help string describing the argument.

        Notes
        -----
        `argparse.Action` subclass constructors must take `dest` as a
        positional argument, but `self.dest` will always be `'editable'`
        for EditableAction instances.
        """
        super().__init__(option_strings, dest, default=default,
                         metavar=metavar, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, 'editable', True)
        setattr(namespace, 'spec', values)


class SubtractAction(Action):
    """
    `argparse.Action` subclass for subtracting from an attribute.

    This action functions as the inverse of the `argparse` module's
    built-in `'count'` action (`argparse._CountAction`). For each
    occurrence of a given keyword argument, it *subtracts* 1 from the
    specified namespace attribute (`dest`). Generally, it can be used to
    implement an argument whose presence negates that of a different
    argument. For example, the `pip install` command accepts both
    `-v`/`--verbose` and `-q`/`--quiet` options, which have opposite
    effects on the stdout generated during installation, and both of
    which may be passed multiple times. Assigning the `'count'` action
    to `-v`/`--verbose`, the `SubtractAction` to `-q`/`--quiet`, and a
    common `dest` to both of the two allows the ultimate verbosity to be
    the net value of the two.
    """

    # noinspection PyShadowingBuiltins
    def __init__(
            self,
            option_strings,
            dest,
            default=None,
            required=False,
            help=None
    ):
        """
        Parameters
        ----------
        option_strings : sequence of str
            Command-line option strings which should be associated with
            this action.
        dest : str
            The name of the attribute to subtract from.
        default : multiple types, optional
            The value to be produced if the option is not specified
            (default: `None`).
        required : bool, optional
            Whether the option must be specified at the command line
            (default: `False`).
        help : str, optional
            The help string describing the argument.
        """
        super().__init__(option_strings=option_strings, dest=dest, nargs=0,
                         default=default, required=required, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        curr_count = getattr(namespace, self.dest, 0)
        setattr(namespace, self.dest, curr_count - 1)


# does not include usage for `pip install [options] -r
# <requirements file> [package-index-options] ...` since it's not
# relevant to `davos` usage
_pip_install_usage = indent(    # noqa: E124 pylint: disable=invalid-name
    dedent("""\
        pip install [options] <requirement specifier> [package-index-options] ...
        pip install [options] [-e] <vcs project url> ...
        pip install [options] [-e] <local project path> ...
        pip install [options] <archive url/path> ..."""
    ), '  '
)

pip_parser = OnionParser(usage=_pip_install_usage,
                         add_help=False,
                         argument_default=SUPPRESS)


# ======== Install Options ========
pip_install_opts = pip_parser.add_argument_group(title="Install Options")
pip_install_opts.add_argument(
    '-c',
    '--constraint',
    metavar='<file>',
    help="Constrain versions using the given constraints file. This option "
         "can be used multiple times."
)
pip_install_opts.add_argument(
    '--no-deps',
    action='store_true',
    help="Don't install package dependencies."
)
pip_install_opts.add_argument(
    '--pre',
    action='store_true',
    help="Include pre-release and development versions. By default, pip only "
         "finds stable versions."
)

spec_or_editable = pip_install_opts.add_mutually_exclusive_group(required=True)
spec_or_editable.add_argument('spec', nargs='?', help=SUPPRESS)
spec_or_editable.add_argument(
    '-e',
    '--editable',
    action=EditableAction,
    default=False,
    metavar='<path/url>',
    help='Install a project in editable mode (i.e. setuptools "develop mode") '
         'from a local project path or a VCS url.'
)

pip_install_opts.add_argument(
    '-t',
    '--target',
    metavar='<dir>',
    help="Install packages into <dir>. By default this will not replace "
         "existing files/folders in <dir>. Use --upgrade to replace existing "
         "packages in <dir> with new versions."
)
pip_install_opts.add_argument(
    '--platform',
    metavar='<platform>',
    help="Only use wheels compatible with <platform>. Defaults to the "
         "platform of the running system. Use this option multiple times to "
         "specify multiple platforms supported by the target interpreter."
)
pip_install_opts.add_argument(
    '--python-version',
    metavar='<python_version>',
    help='The Python interpreter version to use for wheel and '
         '"Requires-Python" compatibility checks. Defaults to a version '
         'derived from the running interpreter. The version can be specified '
         'using up to three dot-separated integers (e.g. "3" for 3.0.0, "3.7" '
         'for 3.7.0, or "3.7.3"). A major-minor version can also be given as '
         'a string without dots (e.g. "37" for 3.7.0).'
)
pip_install_opts.add_argument(
    '--implementation',
    metavar='<implementation>',
    help="Only use wheels compatible with Python implementation "
         "<implementation>, e.g. 'pp', 'jy', 'cp', or 'ip'. If not specified, "
         "then the current interpreter implementation is used. Use 'py' to "
         "force implementation-agnostic wheels."
)
pip_install_opts.add_argument(
    '--abi',
    metavar='<abi>',
    help="Only use wheels compatible with Python abi <abi>, e.g. 'pypy_41'. "
         "If not specified, then the current interpreter abi tag is used. Use "
         "this option multiple times to specify multiple abis supported by "
         "the target interpreter. Generally you will need to specify "
         "--implementation, --platform, and --python-version when using this "
         "option."
)
pip_install_opts.add_argument(
    '--user',
    action='store_true',
    help="Install to the Python user install directory for your platform. "
         "Typically ~/.local/, or %%APPDATA%%Python on Windows. (See the Python "
         "documentation for site.USER_BASE for full details.)"
)
pip_install_opts.add_argument(
    '--root',
    metavar='<dir>',
    help="Install everything relative to this alternate root directory."
)
pip_install_opts.add_argument(
    '--prefix',
    metavar='<dir>',
    help="Installation prefix where lib, bin and other top-level folders are "
         "placed"
)
pip_install_opts.add_argument(
    '--src',
    metavar='<dir>',
    help='Directory to check out editable projects into. The default in a '
         'virtualenv is "<venv path>/src". The default for global installs is '
         '"<current dir>/src".'
)
pip_install_opts.add_argument(
    '-U',
    '--upgrade',
    action='store_true',
    help="Upgrade all specified packages to the newest available version. The "
         "handling of dependencies depends on the upgrade-strategy used."
)
pip_install_opts.add_argument(
    '--upgrade-strategy',
    metavar='<upgrade_strategy>',
    help='Determines how dependency upgrading should be handled [default: '
         'only-if-needed]. "eager" - dependencies are upgraded regardless of '
         'whether the currently installed version satisfies the requirements '
         'of the upgraded package(s). "only-if-needed" - are upgraded only '
         'when they do not satisfy the requirements of the upgraded '
         'package(s).'
)
pip_install_opts.add_argument(
    '--force-reinstall',
    action='store_true',
    help="Reinstall all packages even if they are already up-to-date."
)
pip_install_opts.add_argument(
    '-I',
    '--ignore-installed',
    action='store_true',
    help="Ignore the installed packages, overwriting them. This can break "
         "your system if the existing package is of a different version or "
         "was installed with a different package manager!"
)
pip_install_opts.add_argument(
    '--ignore-requires-python',
    action='store_true',
    help="Ignore the Requires-Python information."
)
pip_install_opts.add_argument(
    '--no-build-isolation',
    action='store_true',
    help="Disable isolation when building a modern source distribution. Build "
         "dependencies specified by PEP 518 must be already installed if this "
         "option is used."
)

pep_517_subgroup = pip_install_opts.add_mutually_exclusive_group()
pep_517_subgroup.add_argument(
    '--use-pep517',
    action='store_true',
    help="Use PEP 517 for building source distributions (use --no-use-pep517 "
         "to force legacy behaviour)."
)
pep_517_subgroup.add_argument(
    '--no-use-pep517',
    action='store_true',
    help=SUPPRESS
)

pip_install_opts.add_argument(
    '--install-option',
    action='append',
    metavar='<options>',
    help='Extra arguments to be supplied to the setup.py install command (use '
         'like --install-option="--install-scripts=/usr/local/bin"). Use '
         'multiple --install-option options to pass multiple options to '
         'setup.py install. If you are using an option with a directory path, '
         'be sure to use absolute path.'
)
pip_install_opts.add_argument(
    '--global-option',
    action='append',
    metavar='<options>',
    help="Extra global options to be supplied to the setup.py call before the "
         "install command."
)

compile_subgroup = pip_install_opts.add_mutually_exclusive_group()
compile_subgroup.add_argument(
    '--compile',
    action='store_true',
    help="Compile Python source files to bytecode"
)
compile_subgroup.add_argument(
    '--no-compile',
    action='store_true',
    help="Do not compile Python source files to bytecode"
)

pip_install_opts.add_argument(
    '--no-warn-script-location',
    action='store_true',
    help="Do not warn when installing scripts outside PATH"
)
pip_install_opts.add_argument(
    '--no-warn-conflicts',
    action='store_true',
    help="Do not warn about broken dependencies"
)
# note: in the actual pip-install implementation, `--no-binary`,
#  `--only-binary`, and `--prefer-binary` triggers a fairly complex
#  callback. But fortunately, we can just store all invocations and
#  forward them to the real pip-install parser
pip_install_opts.add_argument(
    '--no-binary',
    action='append',
    metavar='<format_control>',
    help='Do not use binary packages. Can be supplied multiple times, and '
         'each time adds to the existing value. Accepts either ":all:" to '
         'disable all binary packages, ":none:" to empty the set (notice the '
         'colons), or one or more package names with commas between them (no '
         'colons). Note that some packages are tricky to compile and may fail '
         'to install when this option is used on them.'
)
pip_install_opts.add_argument(
    '--only-binary',
    action='append',
    metavar='<format_control>',
    help='Do not use source packages. Can be supplied multiple times, and '
         'each time adds to the existing value. Accepts either ":all:" to '
         'disable all source packages, ":none:" to empty the set, or one or '
         'more package names with commas between them. Packages without '
         'binary distributions will fail to install when this option is used '
         'on them.'
)
pip_install_opts.add_argument(
    '--prefer-binary',
    action='store_true',
    help="Prefer older binary packages over newer source packages."
)
pip_install_opts.add_argument(
    '--require-hashes',
    action='store_true',
    help="Require a hash to check each requirement against, for repeatable "
         "installs. This option is implied when any package in a requirements "
         "file has a --hash option."
)
pip_install_opts.add_argument(
    '--progress-bar',
    choices=('off', 'on', 'ascii', 'pretty', 'emoji'),
    metavar='<progress_bar>',
    help="Specify type of progress to be displayed "
         "[off|on|ascii|pretty|emoji] (default: on)"
)
pip_install_opts.add_argument(
    '--no-clean',
    action='store_true',
    help="Don’t clean up build directories."
)


# ======== Package Index Options ========
pip_index_opts = pip_parser.add_argument_group(title="Package Index Options")
pip_index_opts.add_argument(
    '-i',
    '--index-url',
    metavar='<url>',
    help="Base URL of the Python Package Index (default "
         "https://pypi.org/simple). This should point to a repository "
         "compliant with PEP 503 (the simple repository API) or a local "
         "directory laid out in the same format."
)
pip_index_opts.add_argument(
    '--extra-index-url',
    action='append',
    metavar='<url>',
    help="Extra URLs of package indexes to use in addition to --index-url. "
         "Should follow the same rules as --index-url."
)
pip_index_opts.add_argument(
    '--no-index',
    action='store_true',
    help="Ignore package index (only looking at --find-links URLs instead)."
)
pip_index_opts.add_argument(
    '-f',
    '--find-links',
    action='append',
    metavar='<url>',
    help="If a URL or path to an html file, then parse for links to archives "
         "such as sdist (.tar.gz) or wheel (.whl) files. If a local path or "
         "file:// URL that’s a directory, then look for archives in the "
         "directory listing. Links to VCS project URLs are not supported."
)


# ======== General Options ========
pip_general_opts = pip_parser.add_argument_group(title='General Options')
pip_general_opts.add_argument(
    '--isolated',
    action='store_true',
    help="Run pip in an isolated mode, ignoring environment variables and "
         "user configuration."
)
# verbose and quiet should theoretically be mutally exclusive, but pip
# itself doesn't seem to implement them as such, so not worth doing so
# here
pip_general_opts.add_argument(
    '-v',
    '--verbose',
    action='count',
    dest='verbosity',
    help="Give more output. Option is additive, and can be used up to 3 times."
)
pip_general_opts.add_argument(
    '-q',
    '--quiet',
    action=SubtractAction,
    dest='verbosity',
    help="Give less output. Option is additive, and can be used up to 3 times "
         "(corresponding to WARNING, ERROR, and CRITICAL logging levels)."
)
pip_general_opts.add_argument(
    '--log',
    metavar='<path>',
    help="Path to a verbose appending log."
)
pip_general_opts.add_argument(
    '--no-input',
    action='store_true',
    help="Disable prompting for input."
)
pip_general_opts.add_argument(
    '--retries',
    type=int,
    metavar='<retries>',
    help="Maximum number of retries each connection should attempt (default 5 "
         "times)."
)
pip_general_opts.add_argument(
    '--timeout',
    type=float,
    metavar='<sec>',
    help="Set the socket timeout (default 15 seconds)."
)
pip_general_opts.add_argument(
    '--exists-action',
    choices=(
        's',
        'switch',
        'i',
        'ignore',
        'w',
        'wipe',
        'b',
        'backup',
        'a',
        'abort'
    ),
    metavar='<action>',
    help="Default action when a path already exists: (s)witch, (i)gnore, "
         "(w)ipe, (b)ackup, (a)bort."
)
pip_general_opts.add_argument(
    '--trusted-host',
    metavar='<hostname>',
    help="Mark this host or host:port pair as trusted, even though it does "
         "not have valid or any HTTPS."
)
pip_general_opts.add_argument(
    '--cert',
    metavar='<path>',
    help="Path to alternate CA bundle."
)
pip_general_opts.add_argument(
    '--client-cert',
    metavar='<path>',
    help="Path to SSL client certificate, a single file containing the "
         "private key and the certificate in PEM format."
)

cache_dir_subgroup = pip_general_opts.add_mutually_exclusive_group()
cache_dir_subgroup.add_argument(
    '--cache-dir',
    metavar='<dir>',
    help="Store the cache data in <dir>."
)
cache_dir_subgroup.add_argument(
    '--no-cache-dir',
    action='store_true',
    help="Disable the cache."
)

pip_general_opts.add_argument(
    '--disable-pip-version-check',
    action='store_true',
    help="Don't periodically check PyPI to determine whether a new version of "
         "pip is available for download. Implied with --no-index."
)

pip_general_opts.add_argument(
    '--no-color',
    action='store_true',
    help="Suppress colored output."
)
pip_general_opts.add_argument(
    '--no-python-version-warning',
    action='store_true',
    help="Silence deprecation warnings for upcoming unsupported Pythons."
)
pip_general_opts.add_argument(
    '--use-feature',
    metavar='<feature>',
    help="Enable new functionality, that may be backward incompatible."
)
pip_general_opts.add_argument(
    '--use-deprecated',
    metavar='<feature>',
    help="Enable deprecated functionality, that will be removed in the future."
)
