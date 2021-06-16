from IPython.core.display import _display_mimetype


def display_reload_warning(pkgs):
    _display_mimetype(
        "application/vnd.colab-display-data+json",
        (
            {'pip_warning': {'packages': ', '.join(pkgs)}},
        ),
        raw=True
    )
