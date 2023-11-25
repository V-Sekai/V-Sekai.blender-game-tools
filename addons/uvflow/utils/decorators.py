from functools import wraps
import time

from uvflow.globals import print_debug


def time_it(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        total_time = time.perf_counter() - start_time
        print_debug(f'Function {func.__name__} Took {total_time:.4f} seconds')
        return result
    return wrapper
