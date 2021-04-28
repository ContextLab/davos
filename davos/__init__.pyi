from collections.abc import Callable
from typing import Literal, Optional
from davos._davos import Davos
from davos.core import PipInstallerKwargs

__all__: list[Literal['activate', 'davos', 'deactivate', 'is_active', 'smuggle']]
__version__: str

davos: Davos
smuggle: Callable[[str, Optional[str], Literal['conda', 'pip'], str, Optional[PipInstallerKwargs]], None]
activate: Callable[[], None]
deactivate: Callable[[], None]
is_active: Callable[[], bool]
