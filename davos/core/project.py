# TODO: add module docstring
from pathlib import Path


DAVOS_CONFIG_DIR = Path.home().joinpath('.davos')
DAVOS_PROJECT_DIR = DAVOS_CONFIG_DIR.joinpath('projects')

class ProjectChecker(type):
    """TODO: add metaclass docstring"""
    def __call__(cls, name):
        cls_to_init = ConcreteProject
        # if user passed a pathlib.Path, convert it to a str so it can
        # be properly expanded, substituted, resolved, etc. below
        name = str(name)
        if PATHSEP in name:
            # `name` is a path to a notebook file, either
            # Project.default() (path to current notebook) or
            # user-specified. File doesn't *have* to exist at this point
            # (will be an AbstractProject, if not), but must at least
            # point to what could eventually be a notebook
            name_path = Path(expandvars(name)).expanduser().resolve(strict=False)
            if name_path.suffix != '.ipynb' or name_path.is_dir():
                # file doesn't have to exist at this point (can be an AbstractProject)
                raise DavosProjectError(
                    f"Invalid project name: '{name}' (which resolves to "
                    f"'{name_path}'). Project names may be either a simple "
                    f"name (without '{PATHSEP}') or a path to a Jupyter "
                    f"notebook (.ipynb) file."
                )
            elif not name_path.is_file():
                cls_to_init = AbstractProject
            name = str(name_path)
        elif PATHSEP_REPLACEMENT in name:
            # `name` is a path-like project directory name read from
            # DAVOS_PROJECT_DIR. Convert back to normal path format to
            # check whether it exists, but don't want to do any
            # validation here in case user somehow ended up with
            # malformed Project dir name, since that could cause
            # incessant errors until manually fixed. Instead, just make
            # it an AbstractProject and let user rename or delete it
            # via davos
            name_path = Path(f"{name.replace(PATHSEP_REPLACEMENT, PATHSEP)}.ipynb")
            if not name_path.is_file():
                cls_to_init = AbstractProject
            name = str(name_path)
        # `name` passed to __init__ is now a str: either a simple name
        # or a fully substituted path to a .ipynb file
        return type.__call__(cls_to_init, name)

class Project:
    """
    A pseudo-environment associated with a particular (set of)
    davos-enhanced notebook(s)
    """
    def __init__(self, name):
        self.name = name
        self.path = Path.home().joinpath

    @property
    def installed_packages(self):
        """pip-freeze-like list of installed packages"""

    def update_name(self):
        """update the project's name to the current notebook name"""


def get_notebook_path():
    # TODO: add docstring
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
        nbserver_root_dir = nbserver_root_dir.strip()

        notebook_api_url = urljoin(nbserver_url, '/api/sessions')
        parsed_url = urlparse(nbserver_url)
        if parsed_url.query:
            params = {'token': parsed_url.query.removeprefix('token=')}
        else:
            params = None

        # TODO: add exception handling, 403 handling, etc.
        response = requests.get(notebook_api_url, params=params)
        for session in response.json():
            if session['kernel']['id'] == kernel_id:
                if config.environment == 'Colaboratory':
                    # Colab notebooks don't actually live on Colab VM
                    # filesystem, so just use notebook name
                    return session['notebook']['name']
                else:
                    notebook_relpath = session['notebook']['path']
                    return Path(nbserver_root_dir, notebook_relpath)


def prune_projects():
    """delete (auto-named) projects for which a notebook doesn't exist"""


def prune_project(proj):
    """delete a single project by its name"""
