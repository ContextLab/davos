from collections.abc import Callable
from io import StringIO
from types import (
    BuiltinFunctionType,
    FunctionType,
    ModuleType,
    TracebackType
)
from typing import (
    Any,
    AnyStr,
    Generic,
    Literal,
    NoReturn,
    Optional,
    overload,
    TextIO,
    Tuple,
    Type,
    TypedDict,
    TypeVar,
    Union
)

__all__: list[
    Literal[
        'capture_stdout',
        'Onion',
        'parse_line',
        'prompt_input',
        'run_shell_command',
    ]
]

_E = TypeVar('_E', bound=BaseException)
_StringOrFileIO = Union[StringIO, TextIO]
_S = TypeVar('_S')

class _SingleStream(tuple[_StringOrFileIO]):
    def __len__(self) -> Literal[1]: ...

class _MultiStream(Tuple[_StringOrFileIO, ...]):
    def __len__(self) -> int: ...

class PipInstallerKwargs(TypedDict, total=False):
    abi: str
    cache_dir: str
    cert: str
    client_cert: str
    compile: bool
    disable_pip_version_check: bool
    editable: bool
    exists_action: Literal['a', 'abort', 'b', 'backup', 'i', 'ignore', 's', 'switch', 'w', 'wipe']
    extra_index_url: list[str]
    find_links: list[str]
    force_reinstall: bool
    global_option: list[str]
    ignore_installed: bool
    ignore_requires_python: bool
    implementation: Literal['cp', 'ip', 'jy', 'pp', 'py']
    index_url: str
    install_option: list[str]
    isolated: bool
    log: str
    no_binary: list[str]
    no_build_isolation: bool
    no_cache_dir: bool
    no_clean: bool
    no_color: bool
    no_compile: bool
    no_deps: bool
    no_index: bool
    no_python_version_warning: bool
    no_use_pep517: bool
    no_warn_conflicts: bool
    no_warn_script_location: bool
    only_binary: list[str]
    platform: str
    pre: bool
    prefer_binary: bool
    prefix: str
    progress_bar: Literal['ascii', 'emoji', 'off', 'on', 'pretty']
    python_version: str
    require_hashes: bool
    retries: int
    root: str
    src: str
    target: str
    timeout: float
    trusted_host: str
    upgrade: bool
    upgrade_strategy: Literal['eager', 'only-if-needed']
    use_deprecated: str
    use_feature: str
    use_pep517: bool
    user: bool
    verbosity: Literal[-3, -2, -1, 0, 1, 2, 3]

class capture_stdout(Generic[_S]):
    closing: bool
    streams: _S
    sys_stdout_write: Callable[[AnyStr], Optional[int]]
    def __init__(self, *streams: _StringOrFileIO, closing: bool = ...) -> None: ...
    @overload
    def __enter__(self: capture_stdout[_SingleStream]) -> _StringOrFileIO: ...
    @overload
    def __enter__(self: capture_stdout[_MultiStream]) -> _MultiStream: ...
    @overload
    def __exit__(self, exc_type: None, exc_value: None, exc_tb: None) -> None: ...
    @overload
    def __exit__(self, exc_type: Type[_E], exc_value: _E, exc_tb: TracebackType) -> bool: ...
    def _write(self, data: AnyStr) -> None: ...

def check_conda() -> None: ...
def get_previously_imported_pkgs(
        install_cmd_stdout: str,
        installer: Literal['conda', 'pip']
) -> list[str]: ...
def import_name(name: str) -> Union[ModuleType, FunctionType, BuiltinFunctionType, Any]: ...

class Onion:
    args_str: str
    build: Optional[str]
    cache_key: str
    import_name: str
    install_name: str
    install_package: Callable[[], str]
    installer: Literal['conda', 'pip']
    installer_kwargs: PipInstallerKwargs
    is_editable: bool
    verbosity: Literal[-3, -2, -1, 0, 1, 2, 3]
    version_spec: str
    @staticmethod
    def parse_onion(onion_text: str) -> tuple[str, str, PipInstallerKwargs]: ...
    def __init__(
            self,
            package_name: str,
            installer: Literal['conda', 'pip'],
            args_str: str,
            **installer_kwargs: Union[bool, float, int, str, list[str]]
    ) -> None: ...
    @property
    def install_cmd(self) -> str: ...
    @property
    def is_installed(self) -> bool: ...
    def _conda_install_package(self) -> NoReturn: ...
    def _pip_install_package(self) -> str: ...

def parse_line(line: str) -> str: ...
def prompt_input(
        prompt: str,
        default: Optional[Literal['n', 'no', 'y', 'yes']] = ...,
        interrupt: Optional[Literal['n', 'no', 'y', 'yes']] = ...
) -> bool: ...
def run_shell_command(command: str, live_stdout: Optional[bool] = ...) -> str: ...
def smuggle(
        name: str,
        as_: Optional[str] = ...,
        installer: Literal['conda', 'pip'] = ...,
        args_str: str = ...,
        installer_kwargs: Optional[PipInstallerKwargs] = ...
) -> None: ...
