# ADD DOCSTRING

# TODO: THIS MODULE SHOULD CONTAIN THE CORRECT IMPLEMENTATION FOR EACH 
#  INTERCHANGEABLE FUNCTION SO THAT OTHER FILES CAN IMPORT FROM HERE

# TODO: add __all__


from davos import config


import_environment = config.environment

if import_environment == 'Python':
    # from davos.implementations.python import (activate_davos, deactivate_davos, run_shell_command, smuggle)
    ...
else:
    from davos.implementations.ipython_common import (
        _run_shell_command_helper, 
        _set_custom_showsyntaxerror,
        _showsyntaxerror_davos,
        check_conda
    )

    _set_custom_showsyntaxerror()
    ...
    if import_environment == 'IPython>=7.0':
        # from davos.implementations.ipython_post7 import ... 
        ...
    else:
        # from davos.implementations.ipython_pre7 import ...
        ...
        if import_environment == 'Colaboratory':
            # from davos.implementations.colab import ...
            ...
        else:
            # from davos.implementations.ipython_pre7 import ...
            ...
