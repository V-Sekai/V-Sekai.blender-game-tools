"""
Copyright (C) 2022 Adobe.
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# file: thread_ops.py
# brief: Threading operations
# author Adobe - 3D & Immersive
# copyright 2022 Adobe Inc. All rights reserved.
# Substance3DInBlender v 1.0.2

import bpy
import queue
import threading


QUEUE_MAIN_THREAD = queue.Queue()
QUEUE_CURSOR = queue.Queue()
QUEUE_CURSOR_ACTIVE = False


class SUBSTANCE_Threads():

    @staticmethod
    def alt_thread_run(function, args):
        _new_thead = threading.Thread(target=function, args=args)
        _new_thead.start()
        return _new_thead

    @staticmethod
    def timer_thread_run(delay_time, function, args):
        _new_thead = threading.Timer(delay_time, function, args=args)
        _new_thead.start()
        return _new_thead

    @staticmethod
    def main_thread_run(function):
        QUEUE_MAIN_THREAD.put(function)

    @staticmethod
    def exec_queued_function():
        while not QUEUE_MAIN_THREAD.empty():
            function = QUEUE_MAIN_THREAD.get()
            function()
        return 0.1

    @staticmethod
    def cursor_push(cursor_name):
        if threading.current_thread() is threading.main_thread():
            global QUEUE_CURSOR_ACTIVE
            if QUEUE_CURSOR_ACTIVE:
                QUEUE_CURSOR.put(cursor_name)
            QUEUE_CURSOR_ACTIVE = True
            bpy.context.window.cursor_modal_set(cursor_name)
        else:
            SUBSTANCE_Threads.main_thread_run(lambda: SUBSTANCE_Threads.cursor_push(cursor_name))

    @staticmethod
    def cursor_pop():
        if threading.current_thread() is threading.main_thread():
            try:
                _cursorName = QUEUE_CURSOR.get(False)
                bpy.context.window.cursor_modal_set(_cursorName)
            except Exception:
                global QUEUE_CURSOR_ACTIVE
                QUEUE_CURSOR_ACTIVE = False
                if bpy.context and bpy.context.window:
                    bpy.context.window.cursor_modal_restore()
        else:
            SUBSTANCE_Threads.main_thread_run(lambda: SUBSTANCE_Threads.cursor_pop())
