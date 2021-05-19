import pkg_resources
from davos.core.config import DavosConfig


__version__ = pkg_resources.get_distribution('davos').version


# config must be instantiated before importing implementations module
config = DavosConfig()


import davos.implementations



def configure(**kwargs): ...
