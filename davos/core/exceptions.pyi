from argparse import ArgumentError
from subprocess import CalledProcessError
from typing import Literal, Optional, Union

__all__: list[
    Literal[
        'DavosError',
        'DavosConfigError',
        'DavosParserError',
        'InstallerError',
        'OnionParserError',
        'OnionArgumentError',
        'ParserNotImplementedError',
        'SmugglerError'
    ]
]

class DavosError(Exception): ...

class DavosConfigError(DavosError): ...

class DavosParserError(SyntaxError, DavosError):
    def __init__(
            self,
            msg: Optional[str] = ...,
            target_text: Optional[str] = ...,
            target_offset: int = ...,
            *args: str
    ) -> None: ...

class OnionParserError(DavosParserError): ...

class OnionArgumentError(ArgumentError, OnionParserError):
    def __init__(
            self,
            msg: Optional[str] = ...,
            argument: Optional[str] = ...,
            onion_txt: Optional[str] = ...,
            *args: str
    ) -> None: ...

class ParserNotImplementedError(OnionParserError, NotImplementedError): ...

class SmugglerError(DavosError): ...

class InstallerError(SmugglerError, CalledProcessError):
    msg: str
    def __init__(
            self,
            msg: str,
            *args: Union[CalledProcessError, str],
            output: Optional[str] = ...,
            stderr: Optional[str] = ...,
            show_stdout: Optional[bool] = ...
    ) -> None: ...
    def __str__(self) -> str: ...
