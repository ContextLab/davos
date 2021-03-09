def smuggle_jupyter():
    raise NotImplementedError("davos does not currently support Jupyter notebooks")


def register_smuggler_jupyter():
    raise NotImplementedError("davos does not currently support Jupyter notebooks")


smuggle_jupyter._register_smuggler = register_smuggler_jupyter
