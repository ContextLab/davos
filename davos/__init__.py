from pkg_resources import get_distribution

from davos._davos import Davos


__all__ = ['davos', 'smuggle']
__version__ = get_distribution('davos').version

davos = Davos()
smuggle = davos.smuggler
