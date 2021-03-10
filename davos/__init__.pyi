from typing import Literal


__all__: list[str]
__version__: str


def determine_environment() -> Literal['PY', 'IPY_NEW', 'IPY_OLD']: ...
