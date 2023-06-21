"""TODO: add module docstring"""

import atexit
import errno
import json
import os
import shutil
import sys
from os.path import expandvars
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import ipykernel
import requests

from davos import config
from davos.core.core import prompt_input, run_shell_command
from davos.core.exceptions import DavosProjectError


__all__ = ['Project', 'get_notebook_path', 'use_default_project']


DAVOS_CONFIG_DIR = Path.home().joinpath('.davos')
DAVOS_PROJECT_DIR = DAVOS_CONFIG_DIR.joinpath('projects')
PATHSEP = os.sep               # '/' for Unix, '\' for Windows
PATHSEP_REPLACEMENT = "___"    # safe replacement for os.sep in dir name
SITE_PACKAGES_SUFFIX = PATHSEP.join((
    'lib',
    f'python{sys.version_info.major}.{sys.version_info.minor}',
    'site-packages'
))


class ProjectChecker(type):
    """
    Metaclass that determines whether the object returned by the
    `Project` constructor will be a `ConcreteProject` or an
    `AbstractProject`
    """
    def __call__(cls, name):
        """TODO: add docstring"""
        cleaned_name, cls_to_init = _get_project_name_type(name)
        # `name` passed to __init__ is now a str: either a simple name
        # or a fully substituted path to a .ipynb file
        return type.__call__(cls_to_init, cleaned_name)


class Project(metaclass=ProjectChecker):
    """
    A pseudo-environment associated with a particular (set of)
    davos-enhanced notebook(s)
    # TODO: future feature: automatic conversion between ConcreteProject
       and AbstractProject reference notebook is moved/created/deleted
    """
    def __init__(self, name):
        """
        TODO: add docstring, note difference between what name can be
         passed as vs what it is when __init__ is run due to metaclass
        """
        self.name = name
        self.safe_name = _filepath_to_safename(name)
        self.project_dir = DAVOS_PROJECT_DIR.joinpath(self.safe_name)
        self.site_packages_dir = self.project_dir.joinpath(SITE_PACKAGES_SUFFIX)
        # eagerly create project dir since it's low-cost
        self.project_dir.mkdir(parents=False, exist_ok=True)
        # register atexit hook to remove project dir if empty
        atexit.register(cleanup_project_dir_atexit, self.project_dir)
        # last modified time of self.site_packages_dir
        self._site_packages_mtime = -1
        # cache of installed packages as of self._site_packages_mtime
        # format: [(name, version), ...]
        self._installed_packages = []

    def __del__(self):
        """
        If the project directory (self.project_dir) is empty, remove it
        when the Project object's reference count drops to 0. Note that
        this can't be relied on, and specifically won't run if the
        Project's __repr__ has appeared in any notebook cell output,
        because IPython caches those outputs internally. The atexit hook
        registered in the constructor takes care of these cases.
         """
        try:
            self.project_dir.rmdir()
        except OSError as e:
            if e.errno == errno.ENOTEMPTY and _dir_is_empty(self.project_dir):
                # project_dir is empty except for a .DS_Store file
                self.project_dir.joinpath('.DS_Store').unlink()
                self.project_dir.rmdir()

    def __eq__(self, other):
        return type(self) is type(other) and self.name == other.name

    def __lt__(self, other):
        # needed for sorting
        if not isinstance(other, Project):
            return NotImplemented
        return self.name < other.name

    def __repr__(self):
        return f"Project({self.name!r})"

    @property
    def installed_packages(self):
        """list of installed packages for the Project"""
        self._refresh_installed_pkgs()
        return self._installed_packages

    def _refresh_installed_pkgs(self):
        """
        update cache of installed packages if site-packages dir has
        been modified since last check
        """
        try:
            site_pkgs_mtime = self.site_packages_dir.stat().st_mtime
        except FileNotFoundError:
            # site-packages dir doesn't exist
            self._installed_packages = []
            return
        if site_pkgs_mtime != self._site_packages_mtime:
            cmd = f'{config.pip_executable} list --path {self.site_packages_dir} --format json'
            pip_list_stdout = run_shell_command(cmd, live_stdout=False)
            try:
                pip_list_json = json.loads(pip_list_stdout)
            except json.JSONDecodeError:
                if pip_list_stdout == '':
                    # no packages installed
                    self._installed_packages = []
                else:
                    raise
            else:
                self._installed_packages = [tuple(pkg.values()) for pkg in pip_list_json]
            self._site_packages_mtime = site_pkgs_mtime

    def freeze(self):
        """pip-freeze-like output for the Project"""
        return '\n'.join('=='.join(pkg) for pkg in self.installed_packages)

    def remove(self, yes=False):
        """
        TODO: add docstring -- remove the project and all installed
         packages. should prompt for confirmation, but accept "yes" arg
         to bypass
        """
        if not yes:
            if config.noninteractive:
                raise DavosProjectError(
                    "To remove a project when noninteractive mode is "
                    "enabled, you must explicitly pass 'yes=True'."
                )
            prompt = f"Remove project {self.name!r} and all installed packages?"
            confirmed = prompt_input(prompt, default='n')
            if not confirmed:
                print(f"{self.name} not removed")
                return
        print(f"Removing {self.project_dir}...")
        shutil.rmtree(self.project_dir)
        if self == config.project:
            self.project_dir.mkdir()

    def rename(self, new_name):
        """
        rename the project and its directory accordingly, possibly
        converting from a ConcreteProject to an AbstractProject or vice
        versa
        """
        new_project_name, new_project_type = _get_project_name_type(new_name)
        if new_project_name == self.name:
            # no change
            return
        new_safe_name = _filepath_to_safename(new_project_name)
        new_project_dir = DAVOS_PROJECT_DIR.joinpath(new_safe_name)
        if new_project_dir.is_dir() and not _dir_is_empty(new_project_dir):
            # new project dir exists and is non-empty
            raise DavosProjectError(
               f"a Project named {new_project_name!r} already exists and "
               "is non-empty. To use this name for another project, first "
               "`.remove()` the existing project."
            )
        # rename the project directory
        self.project_dir.rename(new_project_dir)
        # reload self with new name and type, but retain the installed
        # package cache since we're just renaming the project and not
        # modifying its contents. Note: don't really *need* to do this
        # if `isinstance(self, new_project_type)`, but this way is less
        # likely to introduce bugs in the future if any of the *Project
        # classes' constructors change
        old_installed_pkgs = self._installed_packages
        old_site_pkgs_mtime = self._site_packages_mtime
        # can call type.__call__ directly to bypass metaclass's __call__
        # since we already know the Project's new type
        template_instance = type.__call__(new_project_type, new_project_name)
        self.__class__ = template_instance.__class__
        self.__dict__ = template_instance.__dict__
        self._installed_packages = old_installed_pkgs
        self._site_packages_mtime = old_site_pkgs_mtime
        # explicitly delete the temporary new Project instance so its
        # __del__ method is called before this method returns and we
        # can ensure the project directory exists after reload
        del template_instance
        self.project_dir.mkdir(parents=False, exist_ok=True)


class AbstractProject(Project):
    """
    Project object variant for projects that point to a notebook file
    that doesn't exist. Similar idea to pathlib.PurePath.
    """
    def __getattr__(self, item):
        # Note: stdlib docs say type hint shouldn't be included here
        # https://typing.readthedocs.io/en/latest/source/stubs.html#attribute-access
        if hasattr(ConcreteProject, item):
            msg = f"{item!r} is not supported for abstract projects"
        else:
            msg = f"{self.__class__.__name__!r} object has no attribute {item!r}"
        raise AttributeError(msg)

    def __repr__(self):
        return f"AbstractProject({self.name!r})"


class ConcreteProject(Project):
    """TODO: add docstring"""


def _dir_is_empty(path):
    for p in path.iterdir():
        if p.name != '.DS_Store':
            return False
    return True


def _get_project_name_type(project_name):
    if isinstance(project_name, Path):
        # if user passed a pathlib.Path, convert it to a str so it can
        # be properly expanded, substituted, resolved, etc. below
        project_name = str(project_name)
    elif not isinstance(project_name, str):
        raise TypeError(
            "Project name must be either a str or pathlib.Path, not "
            f"{type(project_name)}"
        )

    if (
            project_name == '' or
            ':' in project_name or
            # disallow backslash on non-Windows systems only
            ('\\' in project_name and os.name != 'nt')
    ):
        raise DavosProjectError(
            f"Invalid project name: '{project_name}'. Names for both Jupyter "
            "notebooks and davos Projects must be at least one character and "
            "may not contain ':' or '\\'."
        )

    project_type = ConcreteProject
    if project_name.endswith('.ipynb'):
        # `project_name` is a path to a notebook file, either the
        # default (absolute path to the current notebook) or
        # user-specified (can be absolute or relative). File doesn't
        # strictly have to exist at this point (and will be an
        # `AbstractProject`, if not), but must at least point to what
        # could eventually be a notebook
        nb_path = Path(expandvars(project_name)).expanduser().resolve()
        if nb_path.is_dir():
            raise DavosProjectError(
                f"Invalid project name: {project_name!r}. Project names ending"
                "in '.ipynb' must point to Jupyter notebook files, but "
                f"'{nb_path}' is a directory."
            )
        if nb_path.stem == '':
            raise DavosProjectError(
                f"Invalid project name: {project_name!r}. '{nb_path}' cannot "
                "be a valid path to a Jupyter notebook because notebook names "
                "must contain at least 1 character."
            )
        if not nb_path.is_file():
            project_type = AbstractProject
        project_name = str(nb_path)
    elif PATHSEP in project_name:
        # if `project_name` doesn't end in '.ipynb' but does contain a
        # PATHSEP, it's either a path to a non-notebook file/directory
        # or a simple name containing '/' (or '\' on Windows), neither
        # of which is valid
        raise DavosProjectError(
            f"Invalid project name: {project_name!r}. Project names may be "
            "either a path to a Jupyter notebook file (ending in '.ipynb') or "
            f"a general name not containing {PATHSEP!r}."
        )
    elif PATHSEP_REPLACEMENT in project_name:
        # `project_name` is a path-like project directory name read from
        # `DAVOS_PROJECT_DIR`. Convert back to normal path format to
        # check whether it exists, but don't do any validation here in
        # case the user somehow ended up with malformed Project
        # directory name, since that could cause impassable errors until
        # manually fixed. Instead, just make it an AbstractProject and
        # let the user rename or delete it via the davos interface.
        nb_path = Path(_safename_to_filepath(project_name))
        if not nb_path.is_file():
            project_type = AbstractProject
        project_name = str(nb_path)

    # otherwise, `project_name` is a simple/general name and no
    # formatting or validation (beyond type and valid character checks
    # above) is needed
    return project_name, project_type


def _filepath_to_safename(filepath):
    """
    Convert a filepath to a project name in "safe" format.

    Takes an absolute path to a notebook file and returns it in a format
    that can be used as a valid directory name. This is the format used
    to name notebook-specific projects directories in
    `davos.DAVOS_PROJECT_DIR`.

    Parameters
    ----------
    filepath : str
        An absolute path to a Jupyter notebook (.ipynb) file.

    Returns
    -------
    str
        The filepath in "safe" format.
    """
    return filepath.replace(PATHSEP, PATHSEP_REPLACEMENT).replace('.ipynb', '')


def _safename_to_filepath(safename):
    """
    Convert a project name in "safe" format to a filepath.

    Takes the name of a notebook-specific project directory in
    `davos.DAVOS_PROJECT_DIR` and returns the path to its associated
    Jupiter notebook file. This is the inverse of
    `_filepath_to_safename()`.

    Parameters
    ----------
    safename : str
        A project directory name in "safe" format.

    Returns
    -------
    str
        The absolute path to the Jupyter notebook (.ipynb) file
        associated with the project.
    """
    return f'{safename.replace(PATHSEP_REPLACEMENT, PATHSEP)}.ipynb'


def get_notebook_path():
    """get the absolute path to the current notebook"""
    kernel_filepath = ipykernel.connect.get_connection_file()
    kernel_id = kernel_filepath.split('/kernel-')[-1].split('.json')[0]

    running_nbservers_stdout = run_shell_command('jupyter notebook list',
                                                 live_stdout=False)
    for line in running_nbservers_stdout.splitlines():
        # should only need to exclude first line ("Currently running
        # servers:"), but handle safely in case output format changes in
        # the future
        if not line.strip().startswith('http'):
            continue

        nbserver_url, nbserver_root_dir = line.split('::')
        nbserver_url = nbserver_url.strip()
        nbserver_root_dir = nbserver_root_dir.strip().rstrip('/')

        notebook_api_url = urljoin(nbserver_url, '/api/sessions')
        parsed_url = urlparse(nbserver_url)
        if parsed_url.query:
            params = {'token': parsed_url.query.replace('token=', '')}
        else:
            params = None

        # TODO: add exception handling, 403 handling, etc.
        response = requests.get(notebook_api_url, params=params, timeout=10)
        for session in response.json():
            if session['kernel']['id'] == kernel_id:
                if config.environment == 'Colaboratory':
                    # Colab notebooks don't actually live on Colab VM
                    # filesystem, so just use notebook name
                    return unquote(session['notebook']['name'])

                notebook_relpath = unquote(session['notebook']['path'])
                return f'{nbserver_root_dir}/{notebook_relpath}'

    # shouldn't ever get here, but just in case
    raise RuntimeError("Could not find notebook path for current kernel")


def cleanup_project_dir_atexit(dirpath):
    """
    TODO: add docstring -- IPython kernel stores internal references to
     objects, so finalizer method isn't called on kernel shutdown. Also
     stores references to objects via its output caching system
     (https://ipython.readthedocs.io/en/stable/interactive/reference.html#output-caching-system).
     This handles those. Function outside class so atexit registry doesn't
     store reference to instance unnecessarily for whole session
    """
    if dirpath.is_dir() and _dir_is_empty(dirpath):
        try:
            dirpath.rmdir()
        except OSError as e:
            if e.errno == errno.ENOTEMPTY:
                # dirpath is empty except for a .DS_Store file
                try:
                    dirpath.joinpath('.DS_Store').unlink()
                except FileNotFoundError:
                    # shouldn't be possible to get here, but silently
                    # handle errors just in case so we don't interfere
                    # with shutdown
                    pass
                else:
                    dirpath.rmdir()


def prune_projects(yes=False):
    """
    Remove unused local projects.

    Delete any notebook-specific projects from `davos.DAVOS_PROJECT_DIR`
    whose corresponding notebooks no longer exist (i.e., any
    `AbstractProject`s). See "Notes" section below for more info.

    Parameters
    ----------
    yes : bool, optional
        If `True` (default: `False`), don't prompt for confirmation
        before removing each unused project.

    Notes
    -----
    1. By default, user confirmation (y/n input) is required before
       deleting each project, but this can be bypassed by passing
       `yes=True`. Note that if davos's non-interactive mode is enabled
       (i.e., `davos.noninteractive` has been set to `True`), `yes=True`
       *must* be explicitly passed to prune projects. This serves as a
       safeguard against unintentionally deleting projects, since
       non-interactive mode disables all user input and confirmation.
    2. The function will also remove any project directories (other than
       the currently active project's) that contain no installed
       packages. However, this is done silently since the intended
       behavior is for empty projects to be removed automatically when
       the interpreter is shut down -- they're only checked for and
       dealt with here as a fallback in case one somehow sneaks through.
    """
    # dict of projects to remove -- keys: "safe"-formatted project
    # directory names; values: corresponding notebook filepaths
    to_remove = {}
    # iterate through project directory and do checks manually rather
    # than checking `davos.all_projects` to avoid creating a bunch of
    # Project instances and registering duplicate `atexit` callbacks
    # unnecessarily
    for project_dir in DAVOS_PROJECT_DIR.iterdir():
        if (
                not project_dir.is_dir()
                or project_dir.name == config._project.safe_name
        ):
            # skip .DS_Store files and the project currently in use
            continue

        project_dirname = project_dir.name
        if PATHSEP_REPLACEMENT in project_dirname:
            # if the project is notebook-specific...
            as_filepath = _safename_to_filepath(project_dirname)
            if not Path(as_filepath).is_file():
                # ... and the associated notebook does not exist (i.e.,
                # it's an "AbstractProject"), mark it for removal
                to_remove[project_dirname] = as_filepath
                continue
        if _dir_is_empty(project_dir):
            # if the project directory is somehow empty, clean it up
            # (see "Notes" section of docstring).
            # Uses `shutil.rmtree()` rather than `Path.rmdir()` to
            # account for potential `.DS_Store` files if the project
            # directory was ever opened in Finder on a Mac
            shutil.rmtree(project_dir, ignore_errors=True)

    if yes:
        # don't list to-be-removed projects or prompt for confirmation
        for project_dirname in to_remove:
            shutil.rmtree(DAVOS_PROJECT_DIR.joinpath(project_dirname))
    elif to_remove:
        # escape codes for styled output
        ANSI_BOLD = '\033[1m'
        ANSI_RED = '\033[31m'
        ANSI_GREEN = '\033[32m'
        ANSI_BLUE = '\033[34m'
        ANSI_YELLOW = '\033[93m'
        ANSI_RESET = '\033[0m'
        RIGHT_ARROW = '\u2192'
        CURRENT_PROJECT_INDICATOR = f'{ANSI_BOLD}{ANSI_BLUE}      {RIGHT_ARROW}{ANSI_RESET}'
        # removed/kept/failed to remove/current selection indicators for
        # each project as they're iteratively processed
        statuses = [CURRENT_PROJECT_INDICATOR] + ["       "] * (len(to_remove) - 1)
        template = f"{ANSI_BOLD}Found {len(to_remove)} unused projects:{ANSI_RESET}"
        for filepath in to_remove.values():
            template = f"{template}\n{{}} AbstractProject({filepath})"

        for i, (project_dirname, as_filepath) in enumerate(to_remove.items()):
            prompt = (
                f"{template.format(*statuses)}\n\n"
                f"Remove {ANSI_BOLD}AbstractProject({as_filepath}){ANSI_RESET}?"
            )
            remove = prompt_input(prompt, default='y')
            if remove:
                try:
                    shutil.rmtree(DAVOS_PROJECT_DIR.joinpath(project_dirname))
                except Exception:
                    statuses[i] = f"{ANSI_BOLD}{ANSI_YELLOW}failed to remove{ANSI_RESET}"
                else:
                    statuses[i] = f"{ANSI_BOLD}{ANSI_RED}removed{ANSI_RESET}"
            else:
                statuses[i] = f"   {ANSI_BOLD}{ANSI_GREEN}kept{ANSI_RESET}"

            if i + 1 < len(to_remove):
                statuses[i + 1] = CURRENT_PROJECT_INDICATOR
            # update project removal statuses and prompt in place
            clear_output(wait=False)
        # print final status for all projects processed
        print(template.format(*statuses))
    else:
        print("No unused projects found.")


def use_default_project():
    """
    Switch (back) to using the default project.

    Determine the default davos Project from the environment and set
    `davos.config.project` to it. In IPython notebooks, this is a
    notebook-specific project named for the notebook's filepath. In an
    IPython shell, this is a project named "ipython-shell", which is
    shared by all IPython shell instances.
    """
    if isinstance(config._ipython_shell, TerminalInteractiveShell):
        proj_name = "ipython-shell"
    else:
        proj_name = get_notebook_path()

    default_project = Project(proj_name)
    config.project = default_project
