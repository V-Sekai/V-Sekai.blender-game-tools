from inspect import isclass
from pkgutil import iter_modules
from pathlib import Path
from importlib import import_module

import bpy

import os
OMI_DEBUG = os.environ.get("OMI_DEBUG", False)

class OMIExtension:
    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension

    def import_gltf_hook(self, root, importer):
        if OMI_DEBUG: print("OVERRIDE: import_gltf_hook", self)
        pass
    def import_node_hook(self, node, blender_object, import_settings):
        if OMI_DEBUG: print("OVERRIDE: import_node_hook", self)
        pass

    def gather_asset_hook(self, asset, export_settings):
        if OMI_DEBUG: print("OVERRIDE: gather_asset_hook", self)
        pass
    def gather_scene_hook(self, root, blender_scene, export_settings):
        if OMI_DEBUG: print("OVERRIDE: gather_scene_hook", self)
        pass
    def gather_node_hook(self, node, blender_object, export_settings):
        if OMI_DEBUG: print("OVERRIDE: gather_node_hook", self)
        pass
    def gather_gltf_hook(self, root, export_settings):
        if OMI_DEBUG: print("OVERRIDE: gather_gltf_hook", self)
        pass

    @staticmethod
    def foreach(array, callback):
        for v in array:
            #print("foreach", callback.__name__, v)
            try:
                callback(v)
            except BaseException as e:
                print("foreach error", callback.__name__, e)

    @staticmethod
    def register_array(array):
        print("... register_all", array)
        OMIExtension.foreach(array, bpy.utils.register_class)

    @staticmethod
    def unregister_array(array):
        print("... unregister_all", array)
        OMIExtension.foreach(array, bpy.utils.unregister_class)

# dynamically scan for registerable bpy.types
def queryRegisterables(all):
    found = []
    for k, v in all.items():
        name = v.__class__.__name__
        if name == "RNAMeta" or name == "RNAMetaPropGroup":
            if OMI_DEBUG: print("queryRegisterables match", v.__module__+"."+v.__name__, name)
            found.append(v)
    return found

# dynamically scan for OMIExtension subclasses in the current directory
def queryExtensions():
    extensions = []
    package_dir = Path(__file__).resolve().parent
    for (_, module_name, _) in iter_modules([package_dir]):
        module = import_module(f"{__name__}.{module_name}")

        if OMI_DEBUG: print("scanning", module_name, f"{__name__}.{module_name}", module is OMIExtension, OMIExtension.__name__)

        for attribute_name in dir(module):
            if attribute_name == "OMIExtension":
                continue
            attribute = getattr(module, attribute_name)
            if isclass(attribute) and issubclass(attribute, OMIExtension):
                print("found omi extension", attribute_name, attribute)
                extensions.append(attribute)
    return extensions

