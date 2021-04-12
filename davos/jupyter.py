# TODO: add module docstring


__all__ = [
    'register_smuggler_jupyter',
    'run_shell_command_jupyter',
    'smuggle_jupyter'
]


from davos.exceptions import ParserNotImplementedError


def register_smuggler_jupyter():
    raise ParserNotImplementedError(
        "davos does not currently support Jupyter notebooks"
    )


def run_shell_command_jupyter(command):
    raise ParserNotImplementedError(
        "davos does not currently support Jupyter notebooks"
    )


def smuggle_jupyter():
    raise NotImplementedError(
        "davos does not currently support Jupyter notebooks"
    )


smuggle_jupyter._register_smuggler = register_smuggler_jupyter
