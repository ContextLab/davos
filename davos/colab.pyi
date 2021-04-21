from typing import Literal, Optional
from google.colab._shell import Shell as ColabShell
from davos.core import PipInstallerKwargs

__all__: list[
    Literal[
        'activate_parser_colab',
        'check_parser_active_colab',
        'deactivate_parser_colab',
        'run_shell_command_colab',
        'smuggle_colab',
        'smuggle_parser_colab'
    ]
]

def _showsyntaxerror_davos(colab_shell: ColabShell, filename: Optional[str] = ...) -> None: ...
def activate_parser_colab() -> None: ...
def check_parser_active_colab() -> bool: ...
def deactivate_parser_colab() -> None: ...
def run_shell_command_colab(command: str) -> Literal[0]: ...
def smuggle_colab(
        name: str,
        as_: Optional[str] = ...,
        installer: [Literal['conda', 'pip']] = ...,
        args_str: str = ...,
        installer_kwargs: Optional[PipInstallerKwargs] = ...
) -> None: ...
def smuggle_parser_colab(line: str) -> str: ...
