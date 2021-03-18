from subprocess import CalledProcessError


class DavosError(Exception):
    pass


class DavosParserError(DavosError):
    # class for errors raised during the parsing step
    pass


class SmugglerError(DavosError):
    # class for errors raised during the smuggle step
    pass


# class InstallerError(SmugglerError, CalledProcessError):
class InstallerError(SmugglerError):
    # class for problems encountered by the installer (pip/conda) itself
    # (e.g., failed to connect to internet, resolve environment, find
    # package with given name, etc.)
    pass


class OnionError(SmugglerError):
    # general class for errors related to the Onion structure/object
    pass


class OnionTypeError(OnionError, TypeError):
    # class analogous to TypeError, but for invalid params specified in
    # Onion construct
    pass


class OnionValueError(OnionError, ValueError):
    # class analogous to ValueError, but for bad values passed to Onion
    # construct params
    pass


class OnionSyntaxError(OnionError, SyntaxError):
    # class analogous to SyntaxError, but for invalid Syntax in Onion
    # construct
    def __init__(self, msg, *args, filename=None, lineno=None, offset=None):
        # TODO: format kwargs into tuple to init super() with correct
        #  format to raise at specific location, see
        #  https://stackoverflow.com/questions/33717804/python-raise-syntaxerror-with-lineno
        super().__init__(msg, *args)
        self.filename = filename
        self.lineno = lineno
        self.offset = offset