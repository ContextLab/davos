"""shared utilities for davos tests"""

import ast
import contextlib
import functools
import html
import inspect
import os
import pkg_resources
import signal
import sys
import types
# use typing generics for compatibility with Python 3.6
from typing import (
    Any,
    Callable,
    Dict, 
    List, 
    NoReturn, 
    Optional, 
    overload, 
    Tuple, 
    TypeVar, 
    Union
)

if sys.version_info.minor < 8:
    from typing_extensions import Literal
else:
    from typing import Literal

import IPython
from IPython.core.ultratb import FormattedTB
from IPython.display import display_html


_E = TypeVar('_E', bound=BaseException)
_F = TypeVar('_F', bound=Callable[..., None])
_InstallerKwargVals = Union[bool, int, str]


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


def mark_timeout(timeout: int = 120) -> Callable[[_F], _F]:
    # stand-in for @pytest.mark.timeout (from pytest-timeout plugin)
    def decorator(func: _F) -> _F:
        def handler(signum: int, frame: Optional[types.FrameType]) -> NoReturn:
            raise TestTimeoutError(
                f"'{func.__name__}' timed out after {timeout} seconds"
            )

        @functools.wraps(func)
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


def run_tests() -> None:
    caller_globals = inspect.currentframe().f_back.f_globals
    tests: List[Tuple[str, types.FunctionType]] = []
    for name, obj in caller_globals.items():
        if name.startswith('test_') and isinstance(obj, types.FunctionType):
            tests.append((name, obj))

    longest_name_len = len(max((t[0] for t in tests), key=len))
    print(f"collected {len(tests)} items\n")
    for test_name, test_func in tests:
        try:
            with open(os.devnull, 'w') as devnull, contextlib.redirect_stdout(devnull):
                test_func()
        except Exception as e:
            tb = format_traceback(e)
            status = f'FAILED\n{tb}\n{"-" * 75}'
        else:
            status = 'PASSED'

        # need at least 1 space between test name and result for parsing
        whitespace = ' ' * (longest_name_len - len(test_name) + 1)
        html_ = (f"<div id='{test_name}_result' style=\"white-space:pre\">"
                 f"{test_name}{whitespace}{status}</div>")
        # noinspection PyTypeChecker
        display_html(html_, raw=True)
