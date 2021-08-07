import bpy
import imp
import string
import random
import re
import os
import pathlib
from mathutils import Vector, Matrix

from . import modifier

from ..utilities import traverse_tree_from_iteration, isclose_matrix, matrix_to_list
from .. import settings

bake_data = {}

class BGE_OT_add_export_action(bpy.types.Operator):
    bl_idname = "ezb.add_export_action"
    bl_label = "New Texture Packer"

    def execute(self, context):
        mod = bpy.context.scene.BGE_Settings.scene_modifiers.BGE_modifier_bake_actions
        mod.export_actions.add()
        index=len(mod.export_actions) - 1
        mod.export_actions_index = index
        return {'FINISHED'}

class BGE_OT_remove_export_action(bpy.types.Operator):
    bl_idname = "ezb.remove_export_action"
    bl_label = "Remove Texture Packer"

    @classmethod
    def poll(cls, context):
        mod = bpy.context.scene.BGE_Settings.scene_modifiers.BGE_modifier_bake_actions
        return len(mod.export_actions) > mod.export_actions_index

    def execute(self, context):
        mod = bpy.context.scene.BGE_Settings.scene_modifiers.BGE_modifier_bake_actions
        mod.export_actions.remove(mod.export_actions_index)

        if mod.export_actions_index >= len(mod.export_actions):
            mod.export_actions_index = len(mod.export_actions)-1
        return {'FINISHED'}


class BGE_ActionCollection(bpy.types.PropertyGroup):
    action: bpy.props.PointerProperty(type=bpy.types.Action)

class BGE_UL_export_actions(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, 'action', emboss=True, text='Action')

class BGE_mod_bake_actions(modifier.BGE_mod_default):
    label = "Export Actions"
    id = 'bake_actions'
    url = "http://renderhjs.net/fbxbundle/#modifier_merge"
    type = 'ARMATURE'
    icon = 'ACTION'
    priority = 2
    tooltip = 'Bakes compatible actions for each bundle and exports them'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    actions_as_separate_files: bpy.props.BoolProperty(
        name='Export as separate files',
        description='Exports each compatible action for each armature into a separate file. Only works with fbx',
        default=True
    )
    try_keep_action_names: bpy.props.BoolProperty(
        name='Try to keep action names',
        description='The FBX exporter by default adds the object name to the animation when it is exported (my_object_name|my_action_name). This option disables that feature. When importing into other game engines the correct action names will appear',
        default=True
    )

    action_validation_mode: bpy.props.EnumProperty(name='Validation Mode', items=[
        ('CORRECT_PATHS', 'Correct Path', 'Checks that all fcurves are valid for the current armature'),
        ('SELECT', 'Select', 'Select the actions that will be exported'),
    ])

    export_actions: bpy.props.CollectionProperty(type=BGE_ActionCollection)
    export_actions_index: bpy.props.IntProperty()
    dependants = [BGE_OT_add_export_action, BGE_OT_remove_export_action, BGE_ActionCollection, BGE_UL_export_actions]

    path: bpy.props.StringProperty(default="{bundle_path}")
    file: bpy.props.StringProperty(default="{action_name}")

    def _is_using_fbx(self, format):
        return format == 'FBX'

    def _warning(self):
        return not self._is_using_fbx(bpy.context.scene.BGE_Settings.export_format)

    def _draw_info(self, layout):
        layout.prop(self, 'actions_as_separate_files')
        if self.actions_as_separate_files:
            row = layout.row()
            row.separator()
            col = row.column(align=True)
            col.prop(self, "path", text="Path")
            col.prop(self, "file", text="File")
        else:
            layout.prop(self, 'try_keep_action_names')
        
        layout.prop(self, 'action_validation_mode')
        if self.action_validation_mode == 'SELECT':
            row = layout.row(align=True)
            row.template_list("BGE_UL_export_actions", "", self, "export_actions", self, "export_actions_index", rows=3)
            col = row.column(align=True)
            col.operator('ezb.add_export_action', text='', icon = 'ADD')
            col.operator('ezb.remove_export_action', text='', icon = 'REMOVE')
            

    def pre_process(self, bundle_info):
        def validate_actions(act, path_resolve):
            if self.action_validation_mode == 'SELECT':
                return any(act == x.action for x in self.export_actions), ''
            elif self.action_validation_mode == 'CORRECT_PATHS':
                for fc in act.fcurves:
                    data_path = fc.data_path
                    if fc.array_index:
                        data_path = data_path + "[%d]" % fc.array_index
                    try:
                        path_resolve(data_path)
                    except ValueError:
                        return False, data_path
                return True, ''

        armatures = bundle_info['armatures']
        for armature in bundle_info['armatures']:

            baked_actions = {}

            for action in bpy.data.actions:
                is_action_valid, error_datapath = validate_actions(action, armature.path_resolve)
                print('{}::{} , valid: {}  {}'.format(armature.name, action.name, is_action_valid, error_datapath))
                if is_action_valid:
                    if not armature.animation_data:
                        armature.animation_data_create()
                    armature.animation_data.action = action

                    baked_actions[action.name] = {}
                    action_data = baked_actions[action.name]

                    for f in range(int(action.frame_range[0]), int(action.frame_range[1] + 1)):
                        if f not in action_data:
                            action_data[f] = []
                        bpy.context.scene.frame_set(f)
                        bpy.context.view_layer.update()
                        # gets the transform of all the bones for each frame
                        # order from root to children here, make array with tuple (bone.name, frame_data) instead of a dictionary for each frame values
                        for bone in traverse_tree_from_iteration(bone for bone in armature.pose.bones if not bone.parent):
                            frame_data = {}
                            parent = bone.parent
                            if parent:
                                # https://blender.stackexchange.com/questions/44637/how-can-i-manually-calculate-bpy-types-posebone-matrix-using-blenders-python-ap
                                created_base_matrix = (parent.matrix.copy() @ (parent.bone.matrix_local.copy().inverted() @ bone.bone.matrix_local))  # this should be like rest pose

                                rot_mat = created_base_matrix.to_quaternion().to_matrix().to_4x4()
                                loc_mat = Matrix.Translation(created_base_matrix.to_translation()).to_4x4()

                                # depending on the inherit scale / rotation/ scale we should create a new base matrrix below
                                # in this case I chose every bone to inherit location and rotation but not scale
                                # created_base_matrix = loc_mat @ rot_mat  # and ignore scaling
                                # all this should be equal to bone.matrix_basis
                                frame_data['created_matrix_basis'] = created_base_matrix.inverted() @ bone.matrix
                                frame_data['original_parent'] = parent.name
                                # if the bone has no parent, this is the matrix that should be applied
                                frame_data['created_matrix_basis_no_parent'] = bone.bone.matrix_local.copy().inverted() @ bone.matrix
                            else:  # TODO: this needs to be deleted
                                frame_data['created_matrix_basis'] = bone.bone.matrix_local.copy().inverted() @ bone.matrix
                                frame_data['created_matrix_basis_no_parent'] = bone.bone.matrix_local.copy().inverted() @ bone.matrix
                                frame_data['original_parent'] = ''

                            frame_data['matrix_world'] = armature.convert_space(pose_bone=bone, matrix=bone.matrix, from_space='POSE', to_space='WORLD')
                            action_data[f].append((bone.name, frame_data))

            bake_data[armature.name] = baked_actions
        
        # now that we stored all the bones transforms, we delete all animation data
        for armature in bundle_info['armatures']:
            # remove all animation data
            armature.animation_data_clear()

            # make all layers visible
            bpy.context.view_layer.objects.active = None
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE', toggle=False)
            for x in range(0, 32):
                armature.data.layers[x] = True

            # make all bones visible
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            for x in armature.data.bones:
                x.hide_select = False
                x.hide = False

            # unlocking all transformations (probably not necessary)
            bpy.ops.object.mode_set(mode='POSE', toggle=False)
            for x in armature.pose.bones:
                x.lock_location = [False, False, False]
                x.lock_rotation = [False, False, False]
                x.lock_rotation_w = False
                x.lock_rotations_4d = False
                x.lock_scale = [False, False, False]

                # delete bone constraints
                constraints = x.constraints[:]
                for y in constraints:
                    x.constraints.remove(y)

            # set inheritance flags
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)
            for x in armature.data.edit_bones:
                # x.parent = None
                x.inherit_scale = 'NONE'
                x.use_inherit_rotation = True
                x.use_local_location = True  # this now should match the matrix we created before
                x.use_connect = False

            # reset transforms of all bones
            bpy.ops.object.mode_set(mode='POSE', toggle=False)
            bpy.ops.pose.select_all(action='SELECT')
            bpy.ops.pose.loc_clear()
            bpy.ops.pose.rot_clear()
            bpy.ops.pose.scale_clear()
        
        

    def process(self, bundle_info):

        armatures = bundle_info['armatures']
        if not armatures:
            return

        if bpy.context.scene.BGE_Settings.export_format != 'FBX':
            bundle_info['export_preset']['bake_anim'] = True

        created_actions = []
        renamed_actions = {}

        for armature in armatures:
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE', toggle=False)

            if armature.name not in bake_data:
                continue

            baked_actions = bake_data[armature.name]
            for action_name, action_data in baked_actions.items():
                print('{} -> applying cached animation "{}"'.format(armature.name, action_name))
                # if the action exists, rename it
                if action_name in bpy.data.actions:
                    temp_name = '_TEMP_{}'.format(action_name)
                    bpy.data.actions[action_name].name = temp_name
                    renamed_actions[temp_name] = action_name
                    self['renamed_actions'] = renamed_actions

                armature.animation_data_create()
                # create a new action
                new_action = bpy.data.actions.new(action_name)
                armature.animation_data.action = new_action
                created_actions.append(action_name)
                self['created_actions'] = created_actions

                bpy.context.view_layer.update()

                # loop though all the actions
                for frame, frame_tuples in action_data.items():
                    for bone_name, frame_data in frame_tuples:
                        bone = armature.pose.bones.get(bone_name)
                        if not bone:
                            continue
                        bone.rotation_mode = 'QUATERNION'
                        if frame_data['original_parent']:
                            if not bone.parent or bone.parent.name != frame_data['original_parent']:
                                print(f'{action_name} -- [{bone_name}] has an incorrect parent??')


                        matrix = frame_data['created_matrix_basis'] if bone.parent and bone.parent.name == frame_data['original_parent'] else frame_data['created_matrix_basis_no_parent']
                        bone.matrix_basis = matrix.copy()

                        # for storing last frame quaternion
                        # uses action_name to store different quaternions for each animation
                        if action_name in bone.keys():
                            quat = bone.rotation_quaternion.copy()
                            quat.make_compatible(bone[action_name])
                            bone.rotation_quaternion = quat
                            bone[action_name] = quat
                            del quat
                        else:
                            bone[action_name] = bone.rotation_quaternion.copy()

                        bone.keyframe_insert("location", index=-1, frame=frame, group=bone.name, options={'INSERTKEY_NEEDED'})
                        bone.keyframe_insert("rotation_quaternion", index=-1, frame=frame, group=bone.name, options={'INSERTKEY_NEEDED'})
                        bone.keyframe_insert("scale", index=-1, frame=frame, group=bone.name, options={'INSERTKEY_NEEDED'})


        # the following processess are only for fbx
        if not self._is_using_fbx(bundle_info['export_format']):
            return

        bundle_info['export_preset']['bake_anim'] = True

        # modifify the way the fbx exporter names actions
        # only useful if not exporting as separate files
        if not self.actions_as_separate_files and self.try_keep_action_names:
            from collections.abc import Iterable
            import io_scene_fbx.export_fbx_bin as fbx
            from io_scene_fbx.fbx_utils import get_bid_name

            def get_blenderID_name(bid):
                if isinstance(bid, Iterable):
                    for i, e in enumerate(bid):
                        if i == len(bid) - 1:
                            return get_bid_name(e)
                else:
                    return get_bid_name(bid)
            fbx.get_blenderID_name = get_blenderID_name

        # export actions as files
        if self.actions_as_separate_files:
            # from fbx addon exporter:
            def validate_actions(act, path_resolve):
                for fc in act.fcurves:
                    data_path = fc.data_path
                    if fc.array_index:
                        data_path = data_path + "[%d]" % fc.array_index
                    try:
                        path_resolve(data_path)
                    except ValueError:
                        return False
                return True

            export_preset = bundle_info['export_preset'].copy()

            export_preset['bake_anim'] = True
            export_preset['bake_anim_use_all_actions'] = False
            export_preset['bake_anim_use_nla_strips'] = False
            export_preset['use_selection'] = True

            for armature in bundle_info['armatures']:
                for act in bpy.data.actions:
                    if validate_actions(act, armature.path_resolve):
                        bpy.context.scene.frame_start = act.frame_range[0]
                        bpy.context.scene.frame_end = act.frame_range[1]
                        folder = self.path.format(bundle_path=bundle_info['path'])
                        file = self.file.format(action_name=act.name)

                        path_full = os.path.join(bpy.path.abspath(folder), file) + "." + settings.export_format_extensions[bundle_info['export_format']]
                        directory = os.path.dirname(path_full)
                        pathlib.Path(directory).mkdir(parents=True, exist_ok=True)

                        export_preset['filepath'] = path_full

                        bpy.context.view_layer.objects.active = None
                        bpy.ops.object.select_all(action="DESELECT")
                        armature.select_set(True)
                        bpy.context.view_layer.objects.active = armature
                        armature.animation_data.action = act
                        settings.export_operators[bundle_info['export_format']](**export_preset)

            # animations are already exported, there is no use in exporting them again for the main fbx file
            bundle_info['export_preset']['bake_anim'] = False

    def post_export(self, bundle_info):
        # remove created actions
        if 'created_actions' in self:
            for x in self['created_actions']:
                bpy.data.actions.remove(bpy.data.actions[x])
            del self['created_actions']

        # if the action already existed, rename it to the original name
        if 'renamed_actions' in self:
            for temp_name, new_name in self['renamed_actions'].items():
                bpy.data.actions[temp_name].name = new_name
            del self['renamed_actions']

        # restore the fbx exporter
        if not self.actions_as_separate_files and self.try_keep_action_names:
            if self._is_using_fbx(bundle_info['export_format']):
                import io_scene_fbx.export_fbx_bin as fbx
                import io_scene_fbx.fbx_utils as utils
                fbx.get_blenderID_name = utils.get_blenderID_name

        # delete bake data
        keys = [x for x in bake_data.keys()]
        for key in keys:
            del bake_data[key]
