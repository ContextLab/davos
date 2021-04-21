from collections.abc import Mapping
from typing import Callable, Literal, Optional
from davos._davos import Davos

__all__: list[Literal['activate', 'davos', 'deactivate', 'is_active', 'smuggle']]
__version__: str

davos: Davos
smuggle: Callable[[str, Optional[str], Literal['pip'], str, Optional[Mapping]], None]
activate: Callable[[], None]
deactivate: Callable[[], None]
is_active: Callable[[], bool]
