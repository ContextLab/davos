from pkg_resources import get_distribution

from davos._davos import Davos


__all__ = ['davos', 'smuggle', 'activate', 'deactivate']
__version__ = get_distribution('davos').version


davos = Davos()
davos.initialize()

smuggle = davos.smuggler
activate = davos.activate_parser
deactivate = davos.deactivate_parser


# TODO: add tree diagram to davos.exceptions module to show class
#  hierarchy
# TODO: Come up with way to supply proper filename, lineno, columnno,
#  etc. to SyntaxErrors and subclasses
# TODO: provide a way to indicate that imported modules should ALSO be
#  parsed by smuggle parser
# TODO: conditionally add arguments to parsers based on user's installed
#  version of installer
# TODO: integrate sensible installer flags into davos behavior (e.g.,
#  logging, verbosity, etc.)
