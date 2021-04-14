# ADD DOCSTRING


__all__ = [
    'activate_parser_jupyter',
    'check_parser_active_jupyter',
    'deactivate_parser_jupyter',
    'run_shell_command_jupyter',
    'smuggle_jupyter',
    'smuggle_parser_jupyter'
]


from davos.exceptions import ParserNotImplementedError


def activate_parser_jupyter():
    raise NotImplementedError(
        "davos does not currently support Jupyter notebooks"
    )


def check_parser_active_jupyter():
    raise NotImplementedError(
        "davos does not currently support Jupyter notebooks"
    )


def deactivate_parser_jupyter():
    raise NotImplementedError(
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


def smuggle_parser_jupyter(line):
    raise ParserNotImplementedError(
        "davos does not currently support Jupyter notebooks"
    )
