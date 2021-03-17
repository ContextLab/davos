"""
TODO: update me
Module for managing session-wide global objects, switches, and
configurable options for both internal and user settings
"""


__all__ = ['Davos']

class Davos:
    def __init__(self):
        try:
            # noinspection PyUnresolvedReferences
            self.ipython_shell = get_ipython()
        except NameError:
            self.ipython_shell = None
            self.parser_environment = 'PY'
            from davos.python import smuggle_python as _smuggle
        else:
            import IPython
            if IPython.version_info[0] < 7:
                # running in Colaboratory or an old IPython/Jupyter
                # Notebook version
                self.parser_environment = 'IPY_OLD'
                from davos.colab import smuggle_colab as _smuggle
            else:
                # running in a new(-ish) IPython/Jupyter Notebook version
                self.parser_environment = 'IPY_NEW'
                from davos.jupyter import smuggle_jupyter as _smuggle
        self.smuggler = _smuggle
        self.smuggler._register()
        self.confirm_install = False
        self.suppress_stdout = False
        self.local_packages = {}
