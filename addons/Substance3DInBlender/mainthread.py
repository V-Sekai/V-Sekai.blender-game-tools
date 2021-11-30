"""
Copyright (C) 2021 Adobe.
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


# Substance 3D in Blender Main Thread
# 4/21/2021
import bpy
import queue
import threading

# post any functions that need to run on the main thread
mainThreadExecutionQueue = queue.Queue()


def RunOnMainThread(function):
    """ Queue a function to run on the main thread """
    mainThreadExecutionQueue.put(function)


def ExecuteQueuedFunction():
    """ Execute all main thread queued functions """
    while not mainThreadExecutionQueue.empty():
        function = mainThreadExecutionQueue.get()
        function()
    return 0.33


# on windows this queue must always be processed on the main thread
cusorQueue = queue.Queue()
cursorQueued = False


def PushCursor(cursorName):
    """ Push a new cursor """
    if threading.current_thread() is threading.main_thread():
        global cursorQueued
        if cursorQueued:
            cusorQueue.put(cursorName)
        cursorQueued = True
        bpy.context.window.cursor_modal_set(cursorName)
    else:
        RunOnMainThread(lambda: PushCursor(cursorName))


def PopCursor():
    """ Pop the current cursor off and restore if the queue is empty """
    if threading.current_thread() is threading.main_thread():
        try:
            cursorName = cusorQueue.get(False)
            bpy.context.window.cursor_modal_set(cursorName)
        except Exception:
            global cursorQueued
            cursorQueued = False
            if bpy.context and bpy.context.window:
                bpy.context.window.cursor_modal_restore()
    else:
        RunOnMainThread(lambda: PopCursor())
