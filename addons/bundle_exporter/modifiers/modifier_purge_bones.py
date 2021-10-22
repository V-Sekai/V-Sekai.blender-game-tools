import bpy
import imp
import string
import random
import re
from mathutils import Vector, Matrix

from . import modifier

from ..utilities import traverse_tree_from_iteration, isclose_matrix, matrix_to_list
from .. import settings


class BGE_mod_purge_bones(modifier.BGE_mod_default):
    label = "Purge Bones"
    id = 'purge_bones'
    url = "http://renderhjs.net/fbxbundle/"
    type = 'ARMATURE'
    icon = 'BONE_DATA'
    priority = -5
    tooltip = 'Deletes specific bones from the armatures'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    delete_non_deforming: bpy.props.BoolProperty(
        name="Delete non deforming",
        default=True
    )

    exclude_prefix: bpy.props.StringProperty(
        name="Prefix",
        description='Any bone with the specified prefix will NOT be deleted',
        default=''
    )

    def _draw_info(self, layout):
        layout.label(text='Delete:')
        row = layout.row()
        row.separator()
        col = row.column()
        col.prop(self, 'delete_non_deforming')
        layout.label(text='Keep:')
        row = layout.row()
        row.separator()
        col = row.column()
        col.prop(self, 'exclude_prefix')
        pass

    def _check_delete_bone(self, bone):
        if self.exclude_prefix and bone.name.startswith(self.exclude_prefix):
            return False

        if not bone.use_deform and self.delete_non_deforming:
            return True

        return False

    def process(self, bundle_info):
        armatures = bundle_info['armatures']

        if not armatures:
            return

        # export all bones by default, this will remove unnecessary ones anyway
        if bundle_info['export_format'] == 'FBX':
            bundle_info['export_preset']['use_armature_deform_only'] = False

        for armature in armatures:
            bpy.context.view_layer.objects.active = None

            bpy.ops.object.select_all(action='DESELECT')
            armature.select_set(True)
            bpy.context.view_layer.objects.active = armature

            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

            delete_bones = [x for x in armature.data.edit_bones if self._check_delete_bone(x)]

            for bone in delete_bones:
                armature.data.edit_bones.remove(bone)

            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        bpy.context.view_layer.objects.active = None
