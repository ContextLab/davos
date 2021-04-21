from typing import Literal, Optional
from google.colab._shell import Shell as ColabShell

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

def _showsyntaxerror_davos(colab_shell: ColabShell, filename: Optional[str] = None) -> None: ...
def activate_parser_colab() -> None: ...
def check_parser_active_colab() -> bool: ...
def deactivate_parser_colab() -> None: ...
def run_shell_command_colab(command: str) -> Literal[0]: ...
def smuggle_colab(
        name: str,
        as_: Optional[str] = None,
        installer: [Literal['pip']] = 'pip',
        args_str: str = '',
        installer_kwargs: Optional[dict[str, ...]] = None
) -> None: ...
def smuggle_parser_colab(line: str) -> str: ...
