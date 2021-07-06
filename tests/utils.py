"""shared utilities for davos tests"""

import ast
import functools
import html
import inspect
import os
import re
from contextlib import redirect_stdout

import pkg_resources
import signal
import sys
import types
from collections.abc import Sequence
# use typing generics for compatibility with Python 3.6
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    NoReturn,
    Optional,
    overload,
    Pattern,
    Tuple,
    Type,
    TypeVar,
    Union
)

if sys.version_info.minor < 8:
    from typing_extensions import Literal, TypedDict
else:
    from typing import Literal, TypedDict

import IPython
from IPython.core.ultratb import FormattedTB
from IPython.display import display_html


_E = TypeVar('_E', bound=BaseException)
_E1 = TypeVar('_E1', bound=BaseException)
_F = TypeVar('_F', bound=Callable[..., None])
_InstallerKwargVals = Union[bool, int, str]
_IpyVersions = Literal['5.5.0', '7.3.0', '7.15', '7.16', 'latest']
_NbTypes = Literal['colab', 'jupyter']


class _DecoratorData(TypedDict):
    name: str
    args: tuple
    kwargs: dict[str, Any]


########################################
#           EXCEPTION CLASSES          #
########################################
class DavosTestingError(Exception):
    """Base class for Davos testing-related errors"""
    pass


class DavosAssertionError(DavosTestingError, AssertionError):
    """Subclasses AssertionError for pytest-specific handling"""
    pass


class TestingEnvironmentError(DavosAssertionError, OSError):
    """Raised due to issues with the testing environment"""
    pass


class TestTimeoutError(DavosAssertionError):
    """Raised if a test exceeds its timeout limit"""
    pass


########################################
#           HELPER FUNCTIONS           #
########################################
def expected_onion_parser_output(
        args_str: str, 
        **installer_kwargs: Union[bool, int, str]
) -> Tuple[str, str, Dict[str, _InstallerKwargVals]]:
    installer_kwargs_ = {'editable': False, 'spec': args_str}
    installer_kwargs_.update(installer_kwargs)
    return '"pip"', f'"""{args_str}"""', installer_kwargs_


def expected_parser_output(
        name: str, 
        as_: Optional[str] = None, 
        args_str: Optional[str] = None, 
        **installer_kwargs: _InstallerKwargVals
) -> str:
    if as_ is not None:
        as_ = f'"{as_}"'
    expected = f'smuggle(name="{name}", as_={as_}'
    if args_str is not None or any(installer_kwargs):
        installer, args_str, inst_kwargs = expected_onion_parser_output(
            args_str, **installer_kwargs
        )
        expected += (f', installer={installer}, '
                     f'args_str={args_str}, '
                     f'installer_kwargs={inst_kwargs}')
    return expected + ')'


def format_traceback(err: _E) -> str:
    tb_formatter = FormattedTB('Context', 'NoColor')
    structured_tb: List[str] = tb_formatter.structured_traceback(
        type(err), err, err.__traceback__
    )
    tb_string: str = tb_formatter.stb2text(structured_tb)
    return html.escape(tb_string)


@overload
def install_davos(
        source: Literal['conda'],
        ref: Optional[str],
        fork: None
) -> NoReturn: ...
@overload
def install_davos(
        source: Literal['github'], 
        ref: Optional[str], 
        fork: Optional[str]
) -> None: ...
@overload
def install_davos(
        source: Literal['pip', 'pypi', 'testpypi'], 
        ref: Optional[str], 
        fork: None
) -> None: ...
def install_davos(
        source: Literal['conda', 'github', 'pip', 'pypi', 'testpypi'] = 'github', 
        ref: Optional[str] = None, 
        fork: Optional[str] = None
) -> None:
    """
    Install a particular version or revision of davos from 
    the specified remote source

    Parameters
    ----------
    source : {'github', 'pip', 'pypi', 'testpypi', 'conda'}, 
             default: 'github'
        The remote source from which to install davos. GitHub 
        is generally used for CI tests, pip/pypi for full 
        releases, and testpypi for test releases

    ref : str, optional
        The version or revision of davos to install. If 
        source is 'github', this can be a branch, commit hash, 
        or tag. Otherwise, this may be a valid version string 
        to install from the given source. Defaults to most 
        recent revision on the default branch of the specified 
        fork (GitHub) or the latest release version (others).

    fork : str, optional
        Optionally, the fork (GitHub username) to install from. 
        Defaults to the base repository (ContextLab). If source 
        is not 'github', this has no effect.

    """    
    source = source.lower()
    if source == 'github':
        if fork is None:
            fork = 'ContextLab'
        name = f'git+https://github.com/{fork}/davos.git'
        if ref is not None:
            name += f'@{ref}'
        name += '#egg=davos'
    elif source in ('pip', 'pypi', 'testpypi'):
        name = 'davos'
        if source == 'testpypi':
            name = '--index-url https://test.pypi.org/simple/ ' + name
        if ref is not None:
            name += f'=={ref}'
    elif source == 'conda':
        raise NotImplementedError(
            "conda installation is not supported in Colaboratory"
        )
    else:
        raise ValueError(f"Invalid source '{source}'")

    # noinspection PyUnresolvedReferences
    return_code: int = IPython.core.interactiveshell.system(f'pip install {name}')
    if return_code != 0:
        raise DavosTestingError(
            f"Failed to install 'davos'. Ran command:\n\t`pip install {name}`"
        )


def is_imported(pkg_name: str) -> bool:
    if pkg_name in sys.modules:
        return True
    elif any(pkg.startswith(f'{pkg_name}.') for pkg in sys.modules):
        return True
    return False


def is_installed(pkg_name: str) -> bool:
    try:
        pkg_resources.get_distribution(pkg_name)
    except pkg_resources.DistributionNotFound:
        return False
    else:
        return True


class mark:
    """
    class that serves as a namespace for test marker decorators.
    Essentially mocks pytest.mark module to preserve similar syntax
    (e.g., pytest.mark.skipif -> utils.mark.skipif)
    """

    _IPYTHON_VERSION: _IpyVersions = get_ipython().user_ns['IPYTHON_VERSION']
    _NOTEBOOK_TYPE: _NbTypes = get_ipython().user_ns['NOTEBOOK_TYPE']

    @staticmethod
    def _set_skiptest_reason(func: _F, reason: str) -> None:
        if hasattr(func, '_skiptest'):
            func._skiptest += f', {reason}'
        else:
            func._skiptest = f'{reason}'

    @classmethod
    def colab(cls, func: _F) -> _F:
        """mark a test that should run only on Google Colab"""
        if cls._NOTEBOOK_TYPE != 'colab':
            cls._set_skiptest_reason(func, "requires Google Colab")
        return func

    @classmethod
    def ipython_post7(cls, func: _F) -> _F:
        """mark a test that should run only if IPython>=7.0.0"""
        if (
                cls._IPYTHON_VERSION != 'latest' and
                int(cls._IPYTHON_VERSION.split('.')[0]) < 7
        ):
            cls._set_skiptest_reason(func, "requires IPython>=7.0.0")
        return func

    @classmethod
    def ipython_pre7(cls, func: _F) -> _F:
        """mark a test that should run only if IPython<7.0.0"""
        if (
                cls._IPYTHON_VERSION == 'latest' or
                int(cls._IPYTHON_VERSION.split('.')[0]) >= 7
        ):
            cls._set_skiptest_reason(func, "requires IPython<7.0.0")
        return func

    @classmethod
    def jupyter(cls, func: _F) -> _F:
        """mark a test that should run only in Jupyter notebooks"""
        if cls._NOTEBOOK_TYPE != 'jupyter':
            cls._set_skiptest_reason(func, "requires Jupyter notebooks")
        return func

    @classmethod
    def skipif(cls, condition: bool, *, reason: str) -> Callable[[_F], _F]:
        """
        mark a test that should be skipped if the given condition
        evaluates to True. Serves as a stand-in for pytest.mark.skipif
        (note: for security reasons, only boolean conditions are
        supported. String conditions are not evaluated)
        """
        def decorator(func: _F) -> _F:
            if condition:
                cls._set_skiptest_reason(func, reason)
            return func

        return decorator

    @staticmethod
    def timeout(timeout: int = 120) -> Callable[[_F], _F]:
        """
        mark a test that should fail after a certain amount of time (in
        seconds). Serves as a stand-in for pytest.mark.timeout (from the
        pytest-timeout plugin)
        """
        def decorator(func: _F) -> _F:
            def handler(signum: int, frame: Optional[types.FrameType]) -> NoReturn:
                raise TestTimeoutError(
                    f"'{func.__name__}' timed out after {timeout} seconds"
                )
            @functools.wraps(func)    # noqa: E306
            def wrapper(*args: Any, **kwargs: Any) -> None:
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(timeout)
                try:
                    return func(*args, **kwargs)
                finally:
                    signal.alarm(0)
            return wrapper
        return decorator


def matches_expected_output(expected: str, result: str) -> bool:
    all_match = True
    expected_chunks = expected.split(';')
    result_chunks = result.split(';')
    assert len(expected_chunks) == len(result_chunks)
    for expected_chunk, result_chunk in zip(expected_chunks, result_chunks):
        if 'installer_kwargs=' in expected_chunk and 'installer_kwargs' in result_chunk:
            exp_kwds: str
            res_kwds: str
            exp_main, exp_kwds = expected_chunk.strip().split('installer_kwargs=')
            res_main, res_kwds = result_chunk.strip().split('installer_kwargs=')
            # remove ')'
            exp_kwargs: Dict[str, _InstallerKwargVals] = ast.literal_eval(exp_kwds[:-1])
            res_kwargs: Dict[str, _InstallerKwargVals] = ast.literal_eval(res_kwds[:-1])
            all_match = all_match and exp_main == res_main and exp_kwargs == res_kwargs
        else:
            all_match = all_match and expected_chunk == result_chunk
    return all_match


class ExceptionInfo(Generic[_E]):
    _common_err_msg = ".{} can only be used after the context manager exits"
    """
    Simplified stand-in for _pytest._code.code.ExceptionInfo. Mocks
    some basic functionality useful in 'raises' context manager.
    """
    def __init__(
            self,
            excinfo: Optional[Tuple[Type[_E], _E, types.TracebackType]]
    ) -> None:
        self._excinfo = excinfo

    @property
    def type(self) -> Type[_E]:
        assert self._excinfo is not None, self._common_err_msg.format('type')
        return self._excinfo[0]

    @property
    def value(self) -> _E:
        assert self._excinfo is not None, self._common_err_msg.format('value')
        return self._excinfo[1]

    @property
    def tb(self) -> types.TracebackType:
        assert self._excinfo is not None, self._common_err_msg.format('tb')
        return self._excinfo[2]

    @property
    def typename(self) -> str:
        assert self._excinfo is not None, self._common_err_msg.format('typename')
        return self.type.__name__

    def match(self, regexp: Union[str, Pattern[str]]) -> Literal[True]:
        exc_str = str(self.value)
        msg = "Regex pattern {!r} does not match {!r}."
        if regexp == exc_str:
            msg += " Did you mean to `re.escape()` the regex?"
        assert re.search(regexp, exc_str), msg.format(regexp, exc_str)
        # return True so method can be asserted from external code
        return True


class raises:
    def __init__(
            self, 
            expected_exception: Union[Type[_E], Tuple[Type[_E]]], 
            *, 
            match: Optional[Union[str, Pattern[str]]] = None
    ) -> None:
        if issubclass(expected_exception, BaseException):
            expected_exception = (expected_exception,)
        elif isinstance(expected_exception, Sequence):
            expected_exception = tuple(expected_exception)
        else:
            raise TypeError(
                "expected_exception may be a exception type or a sequence of "
                "exception types"
            )
        self.expected_exceptions: Tuple[Type[_E]] = expected_exception
        self.match_expr = match
        self.excinfo: Optional[ExceptionInfo[_E]] = None
    
    def __enter__(self) -> ExceptionInfo[_E]:
        self.excinfo = ExceptionInfo(None)
        return self.excinfo

    @overload
    def __exit__(
            self,
            exc_type: None,
            exc_value: None,
            exc_tb: None
    ) -> NoReturn: ...
    @overload    # noqa: E301
    def __exit__(
            self,
            exc_type: Type[_E],
            exc_value: _E,
            exc_tb: types.TracebackType
    ) -> Literal[True]: ...
    @overload    # noqa: E301
    def __exit__(
            self,
            exc_type: Type[_E1],
            exc_value: _E1,
            exc_tb: types.TracebackType
    ) -> Literal[False]: ...
    def __exit__(    # noqa: E301
            self,
            exc_type: Optional[Type[_E]],
            exc_value: Optional[_E],
            exc_tb: Optional[types.TracebackType]
    ) -> bool:
        if exc_type is None:
            raise DavosAssertionError(f"DID NOT RAISE {self.expected_exceptions}")
        elif not issubclass(exc_type, self.expected_exceptions):
            # causes exc_valuue to be raised
            return False
        self.excinfo._excinfo = (exc_type, exc_value, exc_tb)
        if self.match_expr is not None:
            self.excinfo.match(self.match_expr)
        return True


def run_tests() -> None:
    caller_globals = inspect.currentframe().f_back.f_globals
    tests: List[Tuple[str, types.FunctionType]] = []
    for name, obj in caller_globals.items():
        if name.startswith('test_') and isinstance(obj, types.FunctionType):
            tests.append((name, obj))

    longest_name_len = len(max((t[0] for t in tests), key=len))
    print(f"collected {len(tests)} items\n")
    for test_name, test_func in tests:
        # need at least 1 space between test name and result for parsing
        whitespace = ' ' * (longest_name_len - len(test_name) + 1)
        skip_reason: Optional[str] = getattr(test_func, '_skiptest', None)
        if skip_reason is not None:
            reason_esc: str = f"({html.escape(skip_reason)})"
            status = f'SKIPPED{whitespace}{reason_esc}'
        else:
            try:
                with open(os.devnull, 'w') as devnull, redirect_stdout(devnull):
                    test_func()
            except Exception as e:
                tb = format_traceback(e)
                status = f'FAILED\n{tb}\n{"-" * 75}'
            else:
                status = 'PASSED'

        html_ = (f"<div id='{test_name}_result' style=\"white-space:pre\">"
                 f"{test_name}{whitespace}{status}</div>")
        # noinspection PyTypeChecker
        display_html(html_, raw=True)

