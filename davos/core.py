# will hold functions used by all 3 approaches, helper functions, etc.
# once other 2 smugglers are written


class nullcontext:
    """
    dummy context manager equivalent to contextlib.nullcontext
    (which isn't implemented for Python<3.7)
    """
    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, exc_type, exc_value, traceback):
        return None