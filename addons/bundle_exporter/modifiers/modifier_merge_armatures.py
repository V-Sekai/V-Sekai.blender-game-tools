import bpy
import imp
import string
import random
import re
from mathutils import Vector, Matrix

from . import modifier

from ..utilities import traverse_tree_from_iteration, isclose_matrix, matrix_to_list
from .. import settings

from . import modifier_bake_animations


class BGE_mod_merge_armatures(modifier.BGE_mod_default):
    label = "Merge Armatures"
    id = 'merge_armatures'
    url = "http://renderhjs.net/fbxbundle/#modifier_merge"
    type = 'ARMATURE'
    icon = 'CON_ARMATURE'
    priority = -2
    tooltip = 'Merges armatures and actions when exporting'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    create_root_bone: bpy.props.BoolProperty(
        name="Create Root Bone",
        default=True
    )

    root_bone_name: bpy.props.StringProperty(
        name='Root Name',
        default="root"
    )

    rename_bones: bpy.props.BoolProperty(
        name="Rename Bones",
        default=True
    )

    merge_actions: bpy.props.BoolProperty(
        name="Merge Actions",
        default=True
    )

    armature_name: bpy.props.StringProperty(
        name='Armature Name',
        default="MergedArmature"
    )

    new_name: bpy.props.StringProperty(
        name='Bone Name',
        description='Bones will be renamed using this pattern. e.g. my_armature_my_bone',
        default="{armature.name}_{name}"
    )

    action_match_name: bpy.props.StringProperty(
        name='Action Names',
        description='Actions matching this pattern will be merged e.g. "horse_galop" and "human_galop" will be merge into a new animation named "galop"',
        default="{armature.name}_{name}"
    )

    def _draw_info(self, layout):
        col = layout.column(align=False)
        row = col.row(align=True)
        col.prop(self, 'armature_name')

        row.prop(self, 'create_root_bone')
        row.prop(self, 'root_bone_name', text='')

        col.prop(self, "rename_bones", text='Rename Bones')

        if self.rename_bones:
            col.prop(self, "new_name")
        col.prop(self, 'merge_actions')
        if self.merge_actions:
            col.prop(self, "action_match_name")

    def get_new_bone_name(self, armature, bone_name):
        if self.rename_bones:
            return self.new_name.format(armature=armature, name=bone_name)
        return bone_name

    def process(self, bundle_info):
        armatures = bundle_info['armatures']
        objects = bundle_info['meshes']  # for re assigning the armature modfiier
        if not len(armatures) > 1:
            print('Only one armature to merge, process skipped')
            return

        # merge the baked data of all armatures and actions
        baked_merge_actions = {}
        if self.merge_actions:
            # for each armature search corresponding actions
            for armature in armatures:
                if armature.name in modifier_bake_animations.bake_data:
                    # loop though actions to search the ones to merge
                    action_match_pattern = self.action_match_name.format(armature=armature, name='')  # for example: 'myarmature@hand' will search for 'myarmature@' and therefore 'hand' is the name of the action
                    for action_name, action_bake_data in modifier_bake_animations.bake_data[armature.name].items():
                        match = re.search(action_match_pattern, action_name)
                        if match:
                            match = action_name[match.start():match.end()]
                            new_action_name = action_name.replace(match, '')
                            if new_action_name not in baked_merge_actions:
                                baked_merge_actions[new_action_name] = {}
                            print('valid action to merge: {} -> {}'.format(action_name, new_action_name))
                            actions_data = baked_merge_actions[new_action_name]

                            for frame, frame_data in action_bake_data.items():
                                if frame not in actions_data:
                                    actions_data[frame] = []
                                for bone_data in frame_data:
                                    new_parent_name = self.new_name.format(armature=armature, name=bone_data[1]['original_parent'])
                                    bone_data[1]['original_parent'] = new_parent_name
                                    actions_data[frame].append((self.new_name.format(armature=armature, name=bone_data[0]), bone_data[1]))

        # clear the animations data of all the armatures and select them
        bpy.ops.object.select_all(action='DESELECT')
        for x in armatures:
            x.select_set(True)
            if x.animation_data:
                x.animation_data_clear()

        # search for objects that have modifiers pointing to the armatures
        data_to_change = {}
        for x in objects:
            for y in x.modifiers:
                for z in range(1, len(armatures)):
                    o = armatures[z]
                    if hasattr(y, 'object') and y.object == o:
                        if x.name not in data_to_change:
                            data_to_change[x.name] = {}
                        data_to_change[x.name][y.name] = {}
                        data_to_change[x.name][y.name]['object'] = y.object
                        if hasattr(y, 'subtarget'):
                            data_to_change[x.name][y.name]['subtarget'] = y.subtarget

        # rename armature bones (vertex groups should update themselves with this)
        if self.rename_bones:
            for armature in armatures:
                for bone in armature.data.bones:
                    bone.name = self.new_name.format(armature=armature, name=bone.name)

        # join the armatures
        bpy.context.view_layer.objects.active = None
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = armatures[0]
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        for x in armatures:
            x.select_set(True)
        bpy.ops.object.join()

        merged_armature = armatures[0]

        # make the old obj modifiers (like armatures) point to the new armature
        for x in data_to_change:
            obj = bpy.data.objects[x]
            for y in data_to_change[x]:
                mod = obj.modifiers[y]
                mod.object = merged_armature
                if 'subtarget' in data_to_change[x][y]:
                    mod.subtarget = data_to_change[x][y]['subtarget']

        # reset transforms of all bones
        bpy.ops.object.mode_set(mode='POSE', toggle=False)
        for x in merged_armature.pose.bones:
            x.matrix_basis = Matrix.Identity(4)

        # create a new root bone for all the bones
        if self.create_root_bone:
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)
            root_bone = merged_armature.data.edit_bones.new(self.root_bone_name)
            root_bone.head = Vector((0, 0, 0))
            root_bone.tail = Vector((0, 1, 0))
            for x in merged_armature.data.edit_bones:
                if not x.parent and x.name != root_bone:
                    x.parent = root_bone

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # rename armature
        merged_armature.name = self.armature_name
        merged_armature.data.name = self.armature_name + '.data'

        modifier_bake_animations.bake_data[merged_armature.name] = baked_merge_actions

        bundle_info['armatures'] = [merged_armature]
