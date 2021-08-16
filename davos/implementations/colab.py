"""
This modules contains implementations of helper functions specific to
Google Colaboratory notebooks.
"""


__all__ = ['auto_restart_rerun', 'prompt_restart_rerun_buttons']


from IPython.core.display import _display_mimetype


def auto_restart_rerun(pkgs):
    """
    Colab-specific implementation of `auto_restart_rerun`.

    Raises `NotImplementedError` whenever called, though this should
    never happen except when done intentionally as trying to set
    `davos.config.auto_rerun = True` should raise an error. This feature
    is not available in Colab notebooks because it requires accessing
    the notebook frontend through the `colab.global.notebook` JavaScript
    object, which Colab blocks you from doing from the kernel.

    Parameters
    ----------
    pkgs : list of str
        Packages that could not be reloaded without restarting the
        runtime.

    Raises
    -------
    NotImplementedError
        In all cases.
    """
    raise NotImplementedError(
        "automatic rerunning of cells not available in Colaboratory (this "
        "function should not be reachable through normal use)."
    )


def prompt_restart_rerun_buttons(pkgs):
    """
    Colab-specific implementation of `prompt_restart_rerun_buttons`.

    Issues a warning that the notebook runtime must be restarted in
    order to use the just-smuggled version of one or more `pkgs`, and
    displays a button the user can click to do so. Uses one of Colab's
    existing MIME types, since it's one of the few things explicitly
    allowed to send messages between the frontend and kernel.

    Parameters
    ----------
    pkgs : list of str
        Packages that could not be reloaded without restarting the
        runtime.
    """
    _display_mimetype(
        "application/vnd.colab-display-data+json",
        (
            {'pip_warning': {'packages': ', '.join(pkgs)}},
        ),
        raw=True
    )
