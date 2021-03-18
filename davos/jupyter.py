__all__ = [
    'register_smuggler_jupyter',
    'run_shell_command_jupyter',
    'smuggle_jupyter'
]


def register_smuggler_jupyter():
    raise NotImplementedError("davos does not currently support Jupyter notebooks")


def run_shell_command_jupyter(davos_, command, live_stdout=None):
    raise NotImplementedError("davos does not currently support Jupyter notebooks")


def smuggle_jupyter():
    raise NotImplementedError("davos does not currently support Jupyter notebooks")


smuggle_jupyter._register_smuggler = register_smuggler_jupyter
