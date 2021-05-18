import pkg_resources

from davos.core.config import DavosConfig


__version__ = pkg_resources.get_distribution('davos').version


config = DavosConfig()







def configure(**kwargs): ...