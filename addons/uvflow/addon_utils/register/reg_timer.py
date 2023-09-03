from bpy.app import timers
import functools
from time import time


# BUG #33
to_register_timers = []

registered_timers = []


class TimerHandler:
    def __init__(self, timer_callback):
        self.timer = timer_callback

    def stop(self):
        if self.timer and timers.is_registered(self.timer):
            self.timer.stop = True
            timers.unregister(self.timer)
            self.timer = None
        del self


def timer_callback_decorator(decorated_callback):
    def wrapper(*args, **kwargs):
        if hasattr(decorated_callback, 'timeout') and decorated_callback.timeout is not None:
            if time() > decorated_callback.timeout:
                return None
        if hasattr(decorated_callback, 'stop') and decorated_callback.stop:
            return None
        if res := decorated_callback(*args, **kwargs):
            if res == -1:
                return None
            return res
        if hasattr(decorated_callback, 'one_time_only') and decorated_callback.one_time_only:
            return None
        # ret = getattr(decorated_callback, 'step_interval', None)
        # print(decorated_callback.__name__, ret)
        return getattr(decorated_callback, 'step_interval', None)
    return wrapper


def new_timer(callback: callable,
              first_interval: float = 0,
              step_interval: float = 0.1,
              timeout: float = 0,
              one_time_only: bool = True,
              persistent: bool = False,
              args: tuple = (),
              kwargs: dict = {}) -> TimerHandler or None:
    ''' - 'step_interval' and 'timeout' work only if 'one_time_only' is False.
        - If 'timeout' is 0, then won't use it.
        - NOTE: return -1 whenever you want to stop your callback from repeating...
    '''
    if args or kwargs:
        deco_callback = functools.partial(deco_callback, *args, **kwargs)
    if one_time_only:
        deco_callback = callback
        timer_handler = None
    else:
        setattr(callback, 'one_time_only', one_time_only)
        setattr(callback, 'timeout', (time()+timeout+first_interval) if timeout > 0 else None)
        setattr(callback, 'step_interval', step_interval)
        setattr(callback, 'stop', False)
        deco_callback = timer_callback_decorator(callback)
        timer_handler = TimerHandler(deco_callback)
    if args or kwargs:
        # TODO: functools partial.
        timers.register(
            deco_callback,
            first_interval=first_interval,
            persistent=persistent)
    else:
        timers.register(deco_callback, first_interval=first_interval, persistent=persistent)
    registered_timers.append(deco_callback)
    return timer_handler


def new_timer_as_decorator(
    first_interval: float = 0,
    step_interval: float = 0.1,
    timeout: float = 0,
    one_time_only: bool = True,
    persistent: bool = False,
    args: tuple = (),
    kwargs: dict = {}) -> TimerHandler or None:
    
    # def _decorator(callback: callable):
    #     return new_timer(callback, first_interval, step_interval, timeout, one_time_only, persistent, args, kwargs)
    
    def _decorator(callback: callable):
        # BUG #33
        to_register_timers.append((
            callback, first_interval, step_interval, timeout, one_time_only, persistent, args, kwargs
        ))
        return callback
    
    return _decorator


def register():
    # BUG #33
    for timer_data in to_register_timers:
        new_timer(*timer_data)


def unregister():
    for timer in registered_timers:
        if timers.is_registered(timer):
            timers.unregister(timer)
    # registered_timers.clear()
