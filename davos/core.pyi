from collections.abc import Callable
from re import Pattern
from typing import Literal, NoReturn, Optional, TypedDict, Union

__all__: list[Literal['Onion', 'prompt_input', 'smuggle_statement_regex']]

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

class Onion:
    args_str: str
    build: Optional[str]
    import_name: str
    install_name: str
    install_package: Callable[[], tuple[str, int]]
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
    def is_installed(self) -> bool: ...
    def _conda_install_package(self) -> NoReturn: ...
    def _pip_install_package(self) -> tuple[str, int]: ...

def prompt_input(
        prompt: str,
        default: Optional[Literal['n', 'no', 'y', 'yes']] = ...,
        interrupt: Optional[Literal['n', 'no', 'y', 'yes']] = ...
) -> bool: ...

# noinspection PyPep8Naming
class _smuggle_subexprs(TypedDict):
    as_re: Literal[r' +as +[a-zA-Z]\w*']
    comment_re: Literal[r'(?m:\#+.*$)']
    name_re: Literal[r'[a-zA-Z]\w*']
    onion_re: Literal[r'\#+ *pip:.+?(?= +\#| *\n| *$)']
    qualname_re: Literal[r'[a-zA-Z][\w.]*\w']

smuggle_statement_regex: Pattern[str]
