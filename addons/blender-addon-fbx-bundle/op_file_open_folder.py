import bpy, bmesh
import os
import mathutils
import math
from mathutils import Vector
import subprocess

from . import objects_organise


class op(bpy.types.Operator):
    bl_idname = "fbxbundle.file_open_folder"
    bl_label = "Open Folder"
    bl_description = "Open the specified folder"

    @classmethod
    def poll(cls, context):
        if bpy.context.scene.FBXBundleSettings.path == "":
            return False

        return True

    def execute(self, context):
        open_folder(self, bpy.context.scene.FBXBundleSettings.path)

        return {"FINISHED"}


def open_folder(self, path):
    path = os.path.dirname(bpy.path.abspath(path))

    # Warnings
    if not os.path.exists(path):
        self.report({"ERROR_INVALID_INPUT"}, "Path doesn't exist.")
        return

    # Open Folder
    try:
        if os.name == "nt":  # For Windows
            os.startfile(path)
        elif os.name == "posix":  # For Linux, Mac, etc.
            subprocess.check_call(["open", "--", path])
    except Exception as e:
        self.report({"ERROR_INVALID_INPUT"}, str(e))
        return

    print("Open path on system " + path)
