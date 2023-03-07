# TODO: add module docstring
from pathlib import Path


DAVOS_CONFIG_DIR = Path.home().joinpath('.davos')
DAVOS_PROJECT_DIR = DAVOS_CONFIG_DIR.joinpath('projects')


class Project:
    """
    A pseudo-environment associated with a particular (set of)
    davos-enhanced notebook(s)
    """
    def __int__(self, name=None): ...

    @property
    def installed_packages(self):
        """pip-freeze-like list of installed packages"""

    def update_name(self):
        """update the project's name to the current notebook name"""


def get_notebook_path():
    """get the path to the current notebook"""


def prune_projects():
    """delete (auto-named) projects for which a notebook doesn't exist"""


def prune_project(proj):
    """delete a single project by its name"""
