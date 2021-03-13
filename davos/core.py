# will hold functions used by all 3 approaches, helper functions, etc.
# once other 2 smugglers are written





def prompt_input(prompt, default=None, interrupt=None):
    # ADD DOCSTRING
    # NOTE: interrupt applies only to shell interface, not Jupyter/Colab
    response_values = {
        'yes': True,
        'y': True,
        'no': False,
        'n': False
    }
    if interrupt is not None:
        interrupt = interrupt.lower()
        if interrupt not in response_values.keys():
            raise ValueError(
                f"'interrupt' must be one of {tuple(response_values.keys())}"
            )
    if default is not None:
        default = default.lower()
        try:
            default_value = response_values[default]
        except KeyError as e:
            raise ValueError(
                f"'default' must be one of: {tuple(response_values.keys())}"
            ) from e
        response_values[''] = default_value
        opts = '[Y/n]' if default_value else '[y/N]'
    else:
        opts = '[y/n]'

    while True:
        try:
            response = input(f"{prompt}\n{opts} ").lower()
            return response_values[response]
        except KeyboardInterrupt:
            if interrupt is not None:
                return response_values[interrupt]
            else:
                raise
        except KeyError:
            pass






# class nullcontext:
#     """
#     dummy context manager equivalent to contextlib.nullcontext
#     (which isn't implemented for Python<3.7)
#     """
#     def __init__(self, enter_result=None):
#         self.enter_result = enter_result
#
#     def __enter__(self):
#         return self.enter_result
#
#     def __exit__(self, exc_type, exc_value, traceback):
#         return None