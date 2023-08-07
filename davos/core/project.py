"""
"Project" system for isolating smuggled dependencies.

This module implements davos's "Project" scheme for isolating packages
smuggled in a davos-enhanced notebook from the main Python environment,
as well as from those smuggled in other davos-enhanced notebooks.
Functionally, a davos project is similar to Python virtual environment,
with a few main differences:
    - davos projects do not need to be set up, activated, or deactivated
      manually; they are automatically created and used when
      davos-enhanced notebooks are run.
    - davos projects *extend*, rather than replace, the main Python
      environment; they contain only the dependencies of davos-enhanced
      notebooks that are not already satisfied by the packages available
      in those notebooks' "normal" Python environments.
    - davos projects do not contain their own Python or pip executables;
      packages are installed into them using the pip executable from the
      Python environment used to run the notebook kernel.
All davos projects are stored in `davos.DAVOS_PROJECT_DIR`
(`~/.davos/projects/`). By default, each davos-enhanced notebook will
create and use a notebook-specific project named for the path to the
notebook file. Any packages (or specific package versions) smuggled in
that notebook that are not already available in the main Python
environment will be installed into and loaded from the project's
isolated package directory (along with any dependencies of those
packages not already available in the main environment). This way, davos
automatically ensures all smuggled packages and specific package
versions are available at runtime without altering the main Python
environment.

davos projects can also be shared by multiple notebooks. The project
used by the current notebook can be accessed and set via the
`davos.project` (or `davos.config.project`) attribute. When accessed,
the value of `davos.project` will always be a
`davos.core.project.ConcreteProject` instance, but the attribute can
also be assigned either a `str` or `pathlib.Path`, which will be
converted to a `ConcreteProject` internally on assignment. The same
project can be used by multiple notebooks simply by setting
`davos.project` to the same value at the top of each one. While
notebook-specific projects are typically (and by default) named for the
notebook's path, notebook-agnostic projects can be given arbitrary names
(that are not file paths), e.g., `davos.project = "my-project"`.
"""


import atexit
import errno
import json
import os
import shutil
import sys
from os.path import expandvars
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse

import ipykernel
from IPython.display import clear_output
from IPython.terminal.interactiveshell import TerminalInteractiveShell

from davos import config
from davos.core.core import prompt_input, run_shell_command
from davos.core.exceptions import DavosProjectError


__all__ = [
    'DAVOS_CONFIG_DIR',
    'DAVOS_PROJECT_DIR',
    'Project',
    'get_notebook_path',
    'get_project',
    'prune_projects',
    'use_default_project'
]


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
    `AbstractProject`.
    """

    def __call__(cls, name):
        cleaned_name, cls_to_init = _get_project_name_type(name)
        # `name` passed to __init__ is now a str: either a simple name
        # or a fully substituted path to a .ipynb file
        return type.__call__(cls_to_init, cleaned_name)


class Project(metaclass=ProjectChecker):
    """
    A pseudo-environment associated with a particular (set of)
    davos-enhanced notebook(s).
    """

    def __init__(self, name):
        """
        Parameters
        ----------
        name : str or pathlib.Path
            Name of the project. This can be either a simple/general
            name (e.g., "my-project") or a valid path for a Jupyter
            notebook (the path doesn't have to exist, but must end in
            .ipynb). Relative paths, environment variables, symlinks,
            etc. are permitted in paths and will be resolved. Notebook
            paths may also be specified in their "safe" form as they
            appear in `davos.DAVOS_PROJECT_DIR` (i.e., with '/' replaced
            by '___' and '.ipynb' removed).

        Notes
        -----
        The "Parameters" section above describes the valid types and
        formats that may be *passed* to the `Project` constructor to
        specify a path-based name. However, the `ProjectChecker`
        metaclass ensures that when the constructor is actually *run*,
        path-based `name`s will always be a string denoting an absolute
        path.
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
        """
        List packages and versions installed in the project environment.

        Returns a list of all packages installed in the project
        directory as (<pkg_name>, <pkg_version>) tuples. Note that this
        is not necessarily the same as the packages smuggled into the
        current notebook -- it does not include smuggled packages that
        were found in and loaded from the user's main environment, and
        does include dependencies of smuggled packages installed into
        the project directory.
        """
        self._refresh_installed_pkgs()
        return self._installed_packages

    def _refresh_installed_pkgs(self):
        """
        Update cache of installed packages if site-packages dir has
        been modified since last check.
        """
        try:
            site_pkgs_mtime = self.site_packages_dir.stat().st_mtime
        except FileNotFoundError:
            # site-packages dir doesn't exist
            self._installed_packages = []
            return
        if site_pkgs_mtime != self._site_packages_mtime:
            cmd = (
                f'{config.pip_executable} list '
                '--disable-pip-version-check '
                f'--path {self.site_packages_dir} '
                f'--format json'
            )
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
        """Return pip-freeze-like output for the Project."""
        return '\n'.join('=='.join(pkg) for pkg in self.installed_packages)

    def remove(self, yes=False):
        """
        Delete the project and all installed packages.

        Remove the project's directory from `DAVOS_PROJECT_DIR` along
        with all packages installed into it. If the removed project is
        currently in use (i.e., is the Project assigned to
        `davos.project`), the empty project directory is left in place
        rather than deleted immediately so that subsequent `smuggle`
        statements can still install packages into it, if desired. If
        the project directory is still empty when the interpreter
        session ends (or `davos.project` is set to a new value), it is
        then removed.

        Parameters
        ----------
        yes : bool, optional
            If `True` (default: `False`), do not prompt for yes/no
            confirmation before removing the project.

        Notes
        -----
        By default, user confirmation (y/n input) is required before
        deleting a project, but can be bypassed by passing `yes=True`.
        Note that if davos's non-interactive mode is enabled (i.e.,
        `davos.noninteractive` has been set to `True`), `yes=True`
        *must* be explicitly passed to delete the project. This serves
        as a safeguard against unintentionally deleting a project, since
        non-interactive mode disables all user input and confirmation.
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
        shutil.rmtree(self.project_dir)
        if self == config._project:
            self.project_dir.mkdir()

    def rename(self, new_name):
        """
        Rename the project to `new_name`.

        Change the name of the project to `new_name` and rename its
        directory in `DAVOS_PROJECT_DIR` accordingly. The Project's
        Python object is then "reloaded" so these updates are reflected
        in its attribute values, and potentially its type as well.

        Renaming a project has two main use cases:
            1. Editing the name of a non-notebook-specific project
               (i.e., a project with a notebook-agnostic name like
               "stats101-notebooks"), if desired.
            2. Re-linking a notebook-specific project with its
               associated notebook after that notebook has been
               moved or renamed.
        Notebook-specific projects (which davos-enhanced notebooks use
        by default) are named for the path to the notebook whose
        smuggled packages they contain. If that notebook is moved or
        renamed, its associated project will become an `AbstractProject`
        because the path it's associated with (i.e., named for) no
        longer exists. And running the moved/renamed notebook would
        create a new project and reinstall all packages, because there
        would be no project associated with its new path. Instead, the
        existing project can continue to be used by renaming it to match
        the notebook's new path. The project's name, package directory,
        and Python object will be updated to reflect the notebook's
        `new_name`, including converting its type from an
        `AbstractProject` to a `ConcreteProject`.

        Parameters
        ----------
        new_name : str or pathlib.Path
            The new name for the project. This name must not already be
            in use by another project unless that project is empty
            (i.e., no packages have been installed into it).
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
    A Project associated with a notebook file that does not exist.

    davos Projects can be either notebook-specific or notebook-agnostic.
    Notebook-specific projects are named for the absolute path to the
    notebook whose smuggled packages they contain. This serves as a
    convenient, human-readable, unique identifier for linking projects
    to specific notebooks. However, it also means that if a notebook is
    moved, renamed, or deleted, its associated project will point to a
    path that no longer exists. A project in this state is an
    `AbstractProject`. `AbstractProject`s can be created and interacted
    with (e.g., renamed, removed, inspected, etc.) just like "regular"
    projects (i.e., `ConcreteProject`s). However, they cannot be
    assigned to `davos.project` (or `davos.config.project`) and made the
    active project in the current notebook. After moving or renaming a
    notebook, renaming its associated `AbstractProject` to match its new
    filepath will convert it back to a `ConcreteProject`, and cause the
    renamed/moved notebook to continue using it to manage smuggled
    packages.
    """

    def __getattr__(self, item):
        if hasattr(ConcreteProject, item):
            msg = f"{item!r} is not supported for abstract projects"
        else:
            msg = f"{self.__class__.__name__!r} object has no attribute {item!r}"
        raise AttributeError(msg)

    def __repr__(self):
        return f"AbstractProject({self.name!r})"


class ConcreteProject(Project):
    """
    The "normal" Project variant, as opposed to an `AbstractProject`.

    Regular, "non-abstract" projects are instances of this class. It
    mainly exists so that "regular" and "abstract" projects are
    "siblings" on the same level of the class hierarchy, rather than
    `AbstractProject`s being subtypes of "regular" projects.
    Functionally, this makes it easier to dynamically select a `Project`
    class to be instantiated at runtime, and convert existing objects
    between the two types when projects are renamed.

    In conceptualizing davos "projects", the term `ConcreteProject` is
    not used and its instances are simply referred to as "projects".
    Note that unlike the `AbstractProject` class, `ConcreteProject` does
    not redefine the parent `Project` class's `__repr__`, so instances
    of it appear as `Project(<project_name>)`. This is not ambiguous
    with the parent class since instances of it are never actually
    created due the behavior of the `ProjectChecker` metaclass.
    """


def _dir_is_empty(path):
    """
    Check whether a directory is empty, excluding .DS_Store files.

    Parameters
    ----------
    path : pathlib.Path
       The path to the directory to check.

    Returns
    -------
    bool
        Whether the directory is empty (except for possibly a
        `.DS_Store` file).
    """
    for p in path.iterdir():
        if p.name != '.DS_Store':
            return False
    return True


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


def _get_project_name_type(project_name):
    """
    Normalize the project name and determine the project type.

    Handles the various formats in which a project name might be
    specified (e.g., a "simple" name, a path to a notebook file,
    the "safe" name format used for directories in `DAVOS_PROJECT_DIR`,
    etc.) and coerces them into a common format (simple name or absolute
    path, as a string). Determines based on this whether the project
    will be a `ConcreteProject` or `AbstractProject` instance. Also does
    some quick validation of user-specified project names.

    Parameters
    ----------
    project_name : str or pathlib.Path
        The name for the project, as specified by the user or read from
        `DAVOS_PROJECT_DIR`.

    Returns
    -------
    str
        The valid project name in a standardized format: a fully
        substituted, OS-specific, absolute path to a Jupyter notebook
        (.ipynb) file, or a simple/general project name.
    type
        The class of the Project object to be instantiated. If the
        project's name is a path to a notebook file that is
        syntactically valid but does not (yet) exist, the returned class
        will be `AbstractProject`. Otherwise, it will be
        `ConcreteProject`.
    """
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
    if config.environment == 'Colaboratory':
        # colab name/type logic works slightly differently -- there's
        # only ever one "real" notebook per VM session, but it doesn't
        # exist on the VM filesystem
        curr_notebook_name = get_notebook_path()
        if project_name == curr_notebook_name:
            return project_name, project_type
        return project_name, AbstractProject
    if project_name.endswith('.ipynb'):
        # `project_name` is a path to a notebook file, either the
        # default (absolute path to the current notebook) or
        # user-specified (can be absolute or relative). File doesn't
        # strictly have to exist at this point (and will be an
        # `AbstractProject`, if not), but must at least point to what
        # could eventually be a notebook
        nb_path = Path(expandvars(project_name)).expanduser().resolve()
        if nb_path.name == '.ipynb':
            raise DavosProjectError(
                f"Invalid project name: {project_name!r}. A project name "
                "ending in '.ipynb' must be a valid path to a Jupyter "
                "notebook file. Notebook file names must contain at least one "
                "character."
            )
        if nb_path.is_dir():
            raise DavosProjectError(
                f"Invalid project name: {project_name!r}. Project names ending"
                "in '.ipynb' must point to Jupyter notebook files. "
                f"'{nb_path}' is a directory."
            )
        if not nb_path.is_file():
            project_type = AbstractProject
        project_name = str(nb_path)
    elif PATHSEP in project_name or project_name in ('.', '..'):
        # if `project_name` doesn't end in '.ipynb' but does contain a
        # PATHSEP, it's either a path to a non-notebook file/directory
        # or a simple name containing '/' (or '\' on Windows), neither
        # of which is valid. Also catch "." and ".." here, both of which
        # are invalid because they're either relative paths to the CWD &
        # parent dir (rather than a notebook file) or simple names that
        # would be illegal directory names since they're reserved.
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


def cleanup_project_dir_atexit(dirpath):
    """
    Remove project directory on interpreter termination, if empty.

    Each Project instance eagerly creates its `.project_dir` on
    instantiation so it's available for use, then if it isn't used,
    removes it in its finalizer method (`Project.__del__`) to avoid
    cluttering up the user's `DAVOS_PROJECT_DIR` with empty directories.
    However, IPython stores its own internal references to objects in
    the user namespace and releases them after the kernel shuts down and
    this module is unloaded, so Projects that exist at interpreter
    shutdown can't be cleaned up. IPython also stores references to any
    objects that appear in cell outputs via its output caching system
    (https://ipython.readthedocs.io/en/stable/interactive/reference.html#output-caching-system)
    so any Project whose repr is displayed in the notebook also won't
    have its reference count drop to zero before shutdown.

    As a backup, each Project instance registers a call to this function
    with `atexit.register()`, so any empty project dirs that still exist
    at shutdown will be caught and removed. This function is defined
    outside the Project class so the atexit registry doesn't store a
    reference to the instance unnecessarily for the whole session.

    Parameters
    ----------
    dirpath : pathlib.Path
        The path to the project directory to be removed.
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


def get_notebook_path():
    """
    Get the absolute path to the current notebook.

    Use the Jupyter Server REST API and a smidge of the notebook CLI to
    get the path to the current notebook. If running in a Jupyter
    notebook, this returns the absolute path to the notebook file. If
    running in Google Colab notebook, however, this returns just the
    name of the notebook since Colab notebooks don't actually exist on
    the Colab VM filesystem.

    Returns
    -------
    str
        The absolute path (Jupyter) or name (Colab) of the current
    """
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
            # get just the NotebookApp token in case there are multiple parts
            token_param = {'token': parse_qs(parsed_url.query)['token'][0]}
            notebook_api_url = f'{notebook_api_url}?{urlencode(token_param)}'

        with urlopen(notebook_api_url, timeout=10) as response:
            response_data = response.read().decode('utf-8')

        response_json = json.loads(response_data)
        for session in response_json:
            if session['kernel']['id'] == kernel_id:
                if config.environment == 'Colaboratory':
                    # Colab notebooks don't actually live on Colab VM
                    # filesystem, so just use notebook name
                    return unquote(session['notebook']['name'])

                notebook_relpath = unquote(session['notebook']['path'])
                return f'{nbserver_root_dir}/{notebook_relpath}'

    # shouldn't ever get here, but just in case
    raise RuntimeError("Could not find notebook path for current kernel")


def get_project(project_name, create=False):
    """
    Get a Project by its name.

    Return the `Project` instance for the project named `project_name`,
    optionally creating it if it doesn't already exist. If the project
    does not exist and `create` is `False`, return `None`
    (mirrors behavior of built-in `dict.get()`)

    Parameters
    ----------
    project_name : str or pathlib.Path
        The name of the project to get. As is the case when creating a
        new `Project` or setting the `davos.project` field, project
        names that represent notebook filepaths may be provided as an
        absolute or relative path, or in the "safe" name format used for
        directories in `DAVOS_PROJECT_DIR`.
    create : bool, optional
        Whether to create the project if it doesn't already exist
        (default: `False`).

    Returns
    -------
    davos.core.project.Project or None
        The `Project` instance for the project named `project_name`, or
        `None` if the project does not exist and `create` is `False`.

    """
    if create:
        # if we're going to create a Project instance whether the
        # project directory exists or not, no need to check for it first
        return Project(project_name)

    # rather than creating `Project(project_name)` and checking for it
    # in `davos.all_projects`, determine what the project's directory
    # *would* be named and check whether it exists. This avoids creating
    # a bunch of `Project` instances and registering duplicate `atexit`
    # callbacks unnecessarily
    cleaned_name, project_cls = _get_project_name_type(project_name)
    safe_name = _filepath_to_safename(cleaned_name)
    project_dir = DAVOS_PROJECT_DIR.joinpath(safe_name)
    if project_dir.is_dir():
        # since we already got the project's name and type above, we can
        # call `type.__call__` directly and bypass the `ProjectChecker`
        # metaclass's `__call__` method.
        return type.__call__(project_cls, cleaned_name)

    # else, the project doesn't exist
    return None


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
    `davos.project` to it. In IPython notebooks, this is a
    notebook-specific project named for the notebook's filepath. In an
    IPython shell, this is a project named "ipython-shell", which is
    shared by all IPython shell instances.
    """
    if isinstance(config._ipython_shell, TerminalInteractiveShell):
        proj_name = "ipython-shell"
    else:
        proj_name = get_notebook_path()

    # will always be an absolute path to a real Jupyter notebook file,
    # or name of real Colab notebook, so we can skip project type
    # decision logic
    default_project = ConcreteProject(proj_name)
    config.project = default_project
