from collections.abc import Callable
from contextlib import AbstractContextManager
from io import TextIOBase
from types import TracebackType
from typing import Generic, Literal, NoReturn, overload, Protocol, Type, TypeVar, TypedDict

__all__ = list[Literal['capture_stdout', 'check_conda', 'get_previously_imported_pkgs', 'handle_alternate_pip_executable',
                      'import_name', 'Onion', 'parse_line', 'prompt_input', 'run_shell_command', 'use_project', 'smuggle']]

_Exc = TypeVar('_Exc', bound=BaseException)
_Streams = TypeVar('_Streams', bound=tuple[TextIOBase, ...])
_InstallerName = Literal['conda', 'pip']

class SmuggleFunc(Protocol):
    def __call__(self, name: str, as_: str | None = ..., installer: Literal['conda', 'pip'] = ..., args_str: str = ...,
                 installer_kwargs: PipInstallerKwargs | None = ... ) -> None: ...

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

class capture_stdout(Generic[_Streams]):
    closing: bool
    streams: _Streams
    sys_stdout_write: Callable[[str], int | None]
    def __init__(self, *streams: _Streams, closing: bool = ...) -> None: ...
    def __enter__(self) -> _Streams: ...
    @overload
    def __exit__(self, exc_type: None, exc_value: None, exc_tb: None) -> None: ...
    @overload
    def __exit__(self, exc_type: Type[_Exc], exc_value: _Exc, exc_tb: TracebackType) -> bool | None: ...
    def _write(self, data: str) -> None: ...

def check_conda() -> None: ...
def get_previously_imported_pkgs(install_cmd_stdout: str, installer: _InstallerName) -> list[str]: ...
def handle_alternate_pip_executable(installed_name: str) -> AbstractContextManager[None]: ...
def import_name(name: str) -> object: ...

class Onion:
    args_str: str
    build: str | None
    cache_key: str
    import_name: str
    install_name: str
    install_package: Callable[[], str]
    installer: _InstallerName
    installer_kwargs: PipInstallerKwargs
    is_editable: bool
    verbosity: Literal[-3, -2, -1, 0, 1, 2, 3]
    version_spec: str
    @staticmethod
    def parse_onion(onion_text: str) -> tuple[str, str, PipInstallerKwargs]: ...
    def __init__(self, package_name: str, installer: _InstallerName, args_str: str,
                 **installer_kwargs: bool | float | str | list[str]) -> None: ...
    @property
    def install_cmd(self) -> str: ...
    @property
    def is_installed(self) -> bool: ...
    def _conda_install_package(self) -> NoReturn: ...
    def _pip_install_package(self) -> str: ...

def parse_line(line: str) -> str: ...
def prompt_input(prompt: str, default: Literal['n', 'no', 'y', 'yes'] | None = ...,
                 interrupt: Literal['n', 'no', 'y', 'yes'] | None = ...) -> bool: ...
def run_shell_command(command: str, live_stdout: bool | None = ...) -> str: ...
def use_project(smuggle_func: SmuggleFunc) -> SmuggleFunc: ...
def smuggle(name: str, as_: str | None = ..., installer: _InstallerName = ..., args_str: str = ...,
            installer_kwargs: PipInstallerKwargs | None = ...) -> None: ...
