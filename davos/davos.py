import os

def smuggle(module, alias=None, pip_name=None):
    cmd = f'import {module}'
    if alias is not None:
        cmd += f' as {alias}'        
        
    try:
        exec(cmd, globals())
    except ModuleNotFoundError:
        if pip_name is None:
            pip_name = module
            os.system(f'pip install -q -U {pip_name}')
        exec(cmd, globals())