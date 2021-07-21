# ADD DOCSTRING


__all__ = ['auto_restart_rerun_cells', 'prompt_rerun_buttons']


from IPython.core.display import _display_mimetype


def auto_restart_rerun_cells(pkgs):
    raise NotImplementedError(
        "automatic rerunning of cells not available in Colaboratory (this "
        "function should not be reachable through normal use)"
    )


def prompt_restart_rerun_buttons(pkgs):
    _display_mimetype(
        "application/vnd.colab-display-data+json",
        (
            {'pip_warning': {'packages': ', '.join(pkgs)}},
        ),
        raw=True
    )
