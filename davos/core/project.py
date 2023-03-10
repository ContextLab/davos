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
