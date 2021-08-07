import bpy
import math
import imp
import os

from . import modifier


class BGE_mod_rename(modifier.BGE_mod_default):
    label = "Rename"
    id = 'rename'
    url = "http://renderhjs.net/fbxbundle/#modifier_rename"
    type = "GENERAL"
    icon = 'SYNTAX_OFF'
    priority = 998
    tooltip = 'Customize the export path, file name and objects name'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    path: bpy.props.StringProperty(default="{path}")
    file: bpy.props.StringProperty(default="{bundle}")
    obj: bpy.props.StringProperty(default="{object}")

    remove_numbering: bpy.props.BoolProperty(name="Remove numbering from objects", default=True)

    def _draw_info(self, layout):
        col = layout.column(align=True)
        col.prop(self, "path", text="Path")
        col.prop(self, "file", text="File")
        col.prop(self, "obj", text="Object")
        col.prop(self, 'remove_numbering')

    def remove_illegal_characters(self, value):
        chars = '*?"<>|'
        for c in chars:
            value = value.replace(c, '')
        return value

    def format_object_name(self, bundle, name):
        val = self.obj
        val = val.replace("{object}", name)
        val = val.replace("{bundle}", bundle)
        val = val.replace("{scene}", bpy.context.scene.name)
        return self.remove_illegal_characters(val)

    def process_name(self, name):
        if self.remove_numbering and len(name) >= 4 and name[-4] == '.' and name[-3:].isdigit():
            return name[:-4]
        return name

    def process(self, bundle_info):
        path = bundle_info['path']
        name = bundle_info['name']
        objects = bundle_info['meshes'] + bundle_info['empties'] + bundle_info['armatures'] + bundle_info['extras']
        for obj in objects:
            obj.name = self.remove_illegal_characters(self.format_object_name(name, self.process_name(obj.name)))

        new_name = self.file
        new_name = new_name.replace("{bundle}", name)
        new_name = new_name.replace("{scene}", bpy.context.scene.name)
        bundle_info['name'] = self.remove_illegal_characters(new_name)

        new_path = self.path
        new_path = new_path.replace("{path}", path)
        new_path = new_path.replace("{bundle}", name)
        new_path = new_path.replace("{scene}", bpy.context.scene.name)
        bundle_info['path'] = self.remove_illegal_characters(new_path)
