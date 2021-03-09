def smuggle_python():
    raise NotImplementedError("davos does not currently support pure Python interpreters")


def register_smuggler_python():
    raise NotImplementedError("davos does not currently support pure Python interpreters")


smuggle_python._register_smuggler = register_smuggler_python
