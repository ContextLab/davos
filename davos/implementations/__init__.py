# TODO: THIS MODULE SHOULD CONTAIN THE CORRECT IMPLEMENTATION FOR EACH 
#  INTERCHANGEABLE FUNCTION SO THAT OTHER FILES CAN IMPORT FROM HERE


from textwrap import dedent

from davos import config


import_environment = config.environment

if import_environment == 'Python':
    # from davos.implementations.python import (activate_davos, deactivate_davos, run_shell_command, smuggle)
    ...
else:
    from davos.implementations.ipython_common import _showsyntaxerror_davos
    _showsyntaxerror_davos.__doc__ = dedent(f"""\
        ===============================
        
        METHOD UPDATED BY DAVOS PACKAGE
        {_showsyntaxerror_davos.__doc__}
        ===============================
        
        ORIGINAL DOCSTRING:
        {config._ipy_showsyntaxerror_orig.__doc__}\
    """)
    config._ipython_shell.showsyntaxerror = _showsyntaxerror_davos.__get__(config._ipython_shell)
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