# SPDX-License-Identifier: GPL-2.0-or-later

# <pep8 compliant>

bl_info = {
    "name": "Freebird XR",
    "author": "freebirdxr.com",
    "version": (2, 0, 20),
    "blender": (3, 0, 0),
    "location": "3D View > Sidebar > Freebird XR",
    "description": "VR-based 3D modeling add-on",
    "doc_url": "https://freebirdxr.com/beta",
    "category": "3D View",
}

import bpy
import sys
import os

sys.path.append(os.path.dirname(__file__))

import freebird


def register():
    freebird.register()


def unregister():
    freebird.unregister()
