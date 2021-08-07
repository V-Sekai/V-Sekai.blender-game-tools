import bpy
import imp

from . import modifier

from mathutils import Euler

import math


class BGE_mod_unity_rotation_fix(modifier.BGE_mod_default):
    label = "Unity Rotation Fix"
    id = 'unity_rotation_fix'
    url = "http://renderhjs.net/fbxbundle/"
    type = 'GENERAL'
    icon = 'NODE'
    tooltip = 'Fixes rotations of children when exporting to unity'
    priority = 9999999

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    def _draw_info(self, layout):
        pass

    def fix_rotations(self, x):
        parent = x.parent
        x.parent = None

        children = [y for y in x.children]

        for y in children:
            matrixcopy = y.matrix_world.copy()
            y.parent = None
            y.matrix_world = matrixcopy

        bpy.ops.object.select_all(action='DESELECT')
        x.select_set(True)
        bpy.context.view_layer.objects.active = x

        orig_rotation = x.rotation_euler.copy()

        x.rotation_euler = Euler((0.0, 0.0, 0.0), 'XYZ')

        #bpy.ops.object.transform_apply(location=False, rotation=True, scale=False, properties=False)
        bpy.ops.transform.rotate(value=-math.pi / 2, orient_axis='X', constraint_axis=(True, False, False), orient_type='GLOBAL')

        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False, properties=False)

        x.rotation_euler = orig_rotation
        bpy.ops.transform.rotate(value=math.pi / 2, orient_axis='X', constraint_axis=(True, False, False), orient_type='LOCAL')

        if parent:
            x.parent = parent
            x.matrix_parent_inverse = parent.matrix_world.inverted()

        for y in children:
            y.parent = x
            y.matrix_parent_inverse = x.matrix_world.inverted()

        #assert x.name != 'Suzanne.001'

        for child in x.children:
            self.fix_rotations(child)

    def process(self, bundle_info):
        meshes = bundle_info['meshes']

        bpy.context.view_layer.objects.active = None

        parents = [x for x in meshes if x.parent not in meshes]

        for x in parents:
            self.fix_rotations(x)
