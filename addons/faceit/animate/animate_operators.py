import io
import json
import os
import time
from contextlib import redirect_stdout
import timeit

from mathutils import Quaternion, kdtree, Euler, Matrix, Vector
import bpy
import numpy as np
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty, IntProperty, StringProperty)
from bpy_extras.io_utils import ExportHelper
from mathutils import Vector


from ..properties.expression_scene_properties import PROCEDURAL_EXPRESSION_ITEMS

from ..core.pose_utils import reset_pb
from ..core.retarget_list_utils import get_all_set_target_shapes
from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import fc_dr_utils
from ..core import shape_key_utils as sk_utils
from ..core.detection_manager import get_expression_name_double_entries
from ..shape_keys.corrective_shape_keys_utils import (
    CORRECTIVE_SK_ACTION_NAME, clear_all_corrective_shape_keys,
    reevaluate_corrective_shape_keys, remove_corrective_shape_key)
from . import animate_utils as a_utils


mirror_sides_dict_L = {
    'left': 'right',
    'Left': 'Right',
    'LEFT': 'RIGHT',
}
mirror_sides_end_L = {
    'L': 'R',
    '_l': '_r',
}

mirror_sides_dict_R = {
    'right': 'left',
    'Right': 'Left',
    'RIGHT': 'LEFT',
}
mirror_sides_end_R = {
    'R': 'L',
    '_r': '_l',
}


def get_side(expression_name) -> str:
    '''Return the side L/N/R for the given expression name'''
    if any(
            [x in expression_name for x in mirror_sides_dict_L]) or any(
            [expression_name.endswith(x) for x in mirror_sides_end_L]):
        return 'L'
    elif any(
            [x in expression_name for x in mirror_sides_dict_R]) or any(
            [expression_name.endswith(x) for x in mirror_sides_end_R]):
        return 'R'
    else:
        return 'N'


def poll_side_in_expression_name(side, expression_name) -> bool:
    '''Check if the correct side is in the expression name'''
    if side == 'L':
        return any(
            [x in expression_name for x in mirror_sides_dict_L]) or any(
            [expression_name.endswith(x) for x in mirror_sides_end_L])
    if side == "R":
        return any(
            [x in expression_name for x in mirror_sides_dict_R]) or any(
            [expression_name.endswith(x) for x in mirror_sides_end_R])
    return False


def get_mirror_name(side, expression_name):
    '''Return the mirror name for the given expression name and side.'''

    if side == "L":
        for key, value in mirror_sides_dict_L.items():
            if key in expression_name:
                return expression_name.replace(key, value)
        for key, value in mirror_sides_end_L.items():
            if expression_name.endswith(key):
                return expression_name.replace(key, value)

    if side == "R":
        for key, value in mirror_sides_dict_R.items():
            if key in expression_name:
                return expression_name.replace(key, value)
        for key, value in mirror_sides_end_R.items():
            if expression_name.endswith(key):
                return expression_name.replace(key, value)
    return ''


def check_expression_name_valid(self, context) -> None:
    '''Update function that checks for a mirror key.'''
    self.expression_sk_exists = self.expression_name in sk_utils.get_shape_key_names_from_objects()
    self.expression_item_exists = self.expression_name in context.scene.faceit_expression_list
    if self.custom_shape:
        self.side = get_side(self.expression_name)
        if poll_side_in_expression_name(self.side, self.expression_name):
            self.auto_mirror = True
            self.side_suffix_found = True


def check_expression_valid(self, context) -> None:
    '''Update function that checks for a mirror key.'''
    self.expression_sk_exists = self.expression_name in sk_utils.get_shape_key_names_from_objects()
    self.expression_item_exists = self.expression_name in context.scene.faceit_expression_list

    # if poll_side_in_expression_name(self.side, self.expression_name):
    if self.custom_shape:
        self.auto_mirror = self.side_suffix_found = (get_side(self.expression_name) == self.side)


def update_procedural_eyeblinks(self, context) -> None:
    '''Set procedural eyeblinks enum property if set by user'''
    self.procedural = 'EYEBLINKS' if self.procedural_eyeblinks else 'NONE'


class FACEIT_OT_AddExpressionItem(bpy.types.Operator):
    '''Add a new Expression to the expression list and action'''
    bl_idname = "faceit.add_expression_item"
    bl_label = "Add Expression"
    bl_options = {'UNDO', 'INTERNAL'}

    expression_name: StringProperty(
        name="Expression Name",
        default="Expression",
        options={'SKIP_SAVE'},
        update=check_expression_name_valid
    )

    new_exp_index: IntProperty(
        name="Index",
        default=-1,
        options={'SKIP_SAVE'},
    )

    expression_sk_exists: BoolProperty(
        name="Index",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    expression_item_exists: BoolProperty(
        name="Index",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    mirror_name_overwrite: StringProperty(
        name="Mirror Expression Name",
        default="",
        description="force side L/R/N",
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    side: EnumProperty(
        name="Expression Side",
        items=(
            ('L', 'Left', 'Expression affects only left side of the face. (Can create a mirror expression)'),
            ('N', 'All', 'Expression affects the whole face. (Left and right side bones are animated)'),
            ('R', 'Right', 'Expression affects only right side of the face. (Can create a mirror expression)'),
        ),
        default='N',
        update=check_expression_valid
    )

    side_suffix_found: BoolProperty(
        name="Side Suffix Found",
        default=False,
        options={'SKIP_SAVE'}
    )

    custom_shape: BoolProperty(
        name="Single Custom Shape",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    auto_mirror: BoolProperty(
        name="Create Mirror Expression",
        default=False,
        options={'SKIP_SAVE'},
    )
    procedural_eyeblinks: BoolProperty(
        name="Procedural Eye Blinks",
        description="Automatically animate eyeblinks for this expression",
        default=False,
        options={'SKIP_SAVE'},
        update=update_procedural_eyeblinks
    )

    procedural: EnumProperty(
        name="Procedural Expression",
        items=PROCEDURAL_EXPRESSION_ITEMS,
        default='NONE',
        options={'SKIP_SAVE', 'HIDDEN'},
    )

    is_new_rigify_rig: BoolProperty(
        name="Is New Rigify Rig",
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):

        self.expression_item_exists = self.expression_name in context.scene.faceit_expression_list
        self.expression_sk_exists = self.expression_name in sk_utils.get_shape_key_names_from_objects()
        rig = futils.get_faceit_armature()
        if not futils.is_faceit_original_armature(rig):
            if "lip_end.L.001" in rig.pose.bones:
                self.is_new_rigify_rig = True
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "expression_name")
        if self.expression_sk_exists:
            layout.alert = True
            row = layout.row()
            row.label(text="WARNING: Expression Name already in Shape Keys")
        if self.expression_item_exists:
            layout.alert = True
            row = layout.row()
            row.label(text="WARNING: Expression Name already in List.")
        row = layout.row()
        row.prop(self, "side", expand=True, icon='MOD_MIRROR')

        if self.side == 'N':
            box = layout.box()
            row = box.row(align=True)
            row.label(text="The expression can affect both sides.")

        else:
            if poll_side_in_expression_name(self.side, self.expression_name):
                row = layout.row()
                row.prop(self, "auto_mirror", text="Generate Mirror Expression", icon="MOD_MIRROR")
            if not self.side_suffix_found:
                box = layout.box()
                row = box.row(align=True)
                side_suffix = "Left, L, _L or _l" if self.side == 'L' else "Right, R, _R or _r"
                row.label(text="Please add a suffix to the expression name:")
                row = box.row(align=True)
                row.label(text=f"{self.expression_name} + {side_suffix}")
            else:
                row = layout.row()
                row.prop(self, "procedural_eyeblinks", text="Is EyeBlink")

    def execute(self, context):
        scene = context.scene
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False

        expression_list = scene.faceit_expression_list

        shape_action = bpy.data.actions.get("faceit_shape_action")
        ow_action = bpy.data.actions.get("overwrite_shape_action")

        if self.new_exp_index == -1:
            index = len(expression_list)

        frame = int(index + 1) * 10

        expression_name_final = get_expression_name_double_entries(self.expression_name, expression_list)

        # --------------------- Create an Expression Item -----------------------
        item = expression_list.add()
        item.name = expression_name_final
        item.frame = frame
        item.side = self.side
        item.procedural = self.procedural
        if self.mirror_name_overwrite:
            item.mirror_name = self.mirror_name_overwrite

        # --------------------- Custom Expression --------------------------------
        if self.custom_shape:

            if not poll_side_in_expression_name(self.side, self.expression_name):
                self.side = 'N'
            if not item.mirror_name:
                item.mirror_name = get_mirror_name(self.side, expression_name_final)

            if not shape_action:
                shape_action = bpy.data.actions.new("faceit_shape_action")
            if not ow_action:
                ow_action = bpy.data.actions.new("overwrite_shape_action")

            rig = futils.get_faceit_armature()

            if not rig.animation_data:
                rig.animation_data_create()

            for b_name in fdata.FACEIT_BONES:

                if "MCH" in b_name:
                    continue
                if "DEF" in b_name:
                    continue

                base_dp = f"pose.bones[\"{b_name}\"]."
                data_paths = [base_dp + "location", base_dp + "scale", base_dp + "rotation_euler"]
                for dp in data_paths:
                    for i in range(3):
                        fc_dr_utils.get_fcurve_from_bpy_struct(
                            ow_action.fcurves, dp=dp, array_index=i, replace=False)

            if ow_action:
                rig.animation_data.action = ow_action
                a_utils.add_expression_keyframes(rig, frame)

            # Add procedural expression
            if self.procedural != 'NONE':
                bpy.ops.faceit.procedural_eye_blinks(
                    side=self.side,
                    anim_mode='ADD' if self.side == 'N' else 'REPLACE',
                    is_new_rigify_rig=self.is_new_rigify_rig
                )

            if self.auto_mirror and self.side != 'N':
                mirror_side = 'R' if self.side == 'L' else 'L'
                bpy.ops.faceit.add_expression_item(
                    'EXEC_DEFAULT',
                    expression_name=item.mirror_name,
                    custom_shape=True,
                    side=mirror_side,
                    procedural=self.procedural,
                    is_new_rigify_rig=self.is_new_rigify_rig,
                )

            scene.faceit_expression_list_index = index

        else:
            if self.procedural == 'EYEBLINKS':
                bpy.ops.faceit.procedural_eye_blinks(
                    side=self.side,
                    anim_mode='ADD' if self.side == 'N' else 'REPLACE',
                    is_new_rigify_rig=self.is_new_rigify_rig
                )

        scene.tool_settings.use_keyframe_insert_auto = auto_key
        if ow_action:
            scene.frame_start, scene.frame_end = (int(x) for x in futils.get_action_frame_range(ow_action))

        return {'FINISHED'}


class FACEIT_OT_ResetBoneConstraints(bpy.types.Operator):
    '''Set all bone constraints to default values. '''
    bl_idname = "faceit.reset_bone_constraints"
    bl_label = "Reset Bone Constraints"
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return futils.get_faceit_armature()

    def execute(self, context):

        rig = futils.get_faceit_armature()
        a_utils.restore_constraints_to_default_values(rig)

        return {'FINISHED'}


class FACEIT_OT_ChangeExpressionSide(bpy.types.Operator):
    '''Change the expressions side variable. '''
    bl_idname = "faceit.change_expression_side"
    bl_label = "Edit Side"
    bl_options = {'UNDO', 'INTERNAL'}


class FACEIT_OT_MirrorCopy(bpy.types.Operator):
    '''Copy an expression and make them mirrored expressions. Only works for expressions assigned to L/R'''
    bl_idname = "faceit.mirror_copy_expression"
    bl_label = "Mirror Copy Expression"
    bl_options = {'UNDO', 'INTERNAL'}


class FACEIT_OT_EmptyExpressionsFromShapeKeys(bpy.types.Operator):
    '''Copy an expression and make them mirrored expressions. Only works for expressions assigned to L/R'''
    bl_idname = "faceit.empty_expressions_from_shape_keys"
    bl_label = "Copy Empty Expression"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        obj = context.object
        if not obj:
            self.report({'ERROR'}, "You need to select an object with shape keys.")
            return {'CANCELLED'}
        if not sk_utils.has_shape_keys(obj):
            self.report({"ERROR"}, f"Object {obj.name} has no shape keys.")
            return {"CANCELLED"}

        for sk in obj.data.shape_keys.key_blocks:
            if sk.name == 'Basis':
                continue
            expression_name = sk.name  # [len('m_head_mid_'):]
            side = get_side(expression_name)
            bpy.ops.faceit.add_expression_item(
                'EXEC_DEFAULT',
                expression_name=expression_name,
                custom_shape=True,
                side=side,
            )
        return {'FINISHED'}


class FACEIT_OT_MoveExpressionItem(bpy.types.Operator):
    '''Move a specific Expression Item index in the list. Also effects the expression actions '''
    bl_idname = "faceit.move_expression_item"
    bl_label = "Move"
    bl_options = {'UNDO', 'INTERNAL'}

    # the name of the facial part
    direction: bpy.props.EnumProperty(
        items=(
            ('UP', 'Up', ''),
            ('DOWN', 'Down', ''),
        ),
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        idx = context.scene.faceit_expression_list_index
        expression_list = context.scene.faceit_expression_list

        # if idx > 0 and idx <= len(context.scene.faceit_expression_list):
        #     return True
        return expression_list and idx >= 0 and idx < len(expression_list)

    def move_index(self, context, flist, index):
        '''Move the item at index'''
        list_length = len(flist) - 1
        new_index = index + (-1 if self.direction == 'UP' else 1)
        context.scene.faceit_expression_list_index = max(0, min(new_index, list_length))

    def execute(self, context):
        scene = context.scene
        index = scene.faceit_expression_list_index
        expression_list = scene.faceit_expression_list
        expression_item = expression_list[index]

        add_index = -1 if self.direction == 'UP' else 1
        new_index = index + add_index
        add_frame = add_index * 10

        if new_index == len(expression_list) or new_index == -1:
            return {'CANCELLED'}
            # self.report({'ERROR'},)

        new_index_item = expression_list[new_index]

        ow_action = bpy.data.actions.get("overwrite_shape_action")
        sh_action = bpy.data.actions.get("faceit_shape_action")
        cc_action = bpy.data.actions.get(CORRECTIVE_SK_ACTION_NAME)

        # original frame
        expression_frame = expression_item.frame
        new_index_frame = new_index_item.frame

        actions = [ow_action, sh_action]

        for action in actions:
            if action:
                for curve in action.fcurves:
                    for key in curve.keyframe_points:
                        if key.co[0] == new_index_frame:
                            key.co[0] -= add_frame / 2
                    for key in curve.keyframe_points:
                        if key.co[0] == expression_frame:
                            key.co[0] += add_frame
                    for key in curve.keyframe_points:
                        if key.co[0] == new_index_frame - add_frame / 2:
                            key.co[0] -= add_frame / 2

                for curve in action.fcurves:
                    curve.update()
        if cc_action:
            exp_fc = cc_action.fcurves.find(f"key_blocks[\"faceit_cc_{expression_item.name}\"].value")
            if exp_fc:
                for key in exp_fc.keyframe_points:
                    key.co[0] += add_frame
                exp_fc.update()

            new_index_fc = cc_action.fcurves.find(f"key_blocks[\"faceit_cc_{new_index_item.name}\"].value")
            if new_index_fc:
                for key in new_index_fc.keyframe_points:
                    key.co[0] -= add_frame
                new_index_fc.update()

        expression_item.frame = new_index_frame
        new_index_item.frame = expression_frame

        expression_list.move(new_index, index)
        self.move_index(context, expression_list, index)
        return {'FINISHED'}


class FACEIT_OT_AppendActionToFaceitRig(bpy.types.Operator):
    ''' Load a compatible Faceit Expression Action to the Faceit Armature Object. Creates two actions (faceit_shape_action, overwrite_shape_action) '''
    bl_idname = "faceit.append_action_to_faceit_rig"
    bl_label = "Load Faceit Expressions"
    bl_options = {'UNDO', 'INTERNAL'}

    expressions_type: EnumProperty(
        name='Expressions',
        items=(('ARKIT', "ARKit", "The 52 ARKit Expressions that are used in all iOS motion capture apps"),
               ('A2F', "Audio2Face", "The 46 expressions that are used in Nvidias Audio2Face app by default."),
               ('TONGUE', "Tongue", "12 Tongue Expressions that can add realism to speech animation"),
               ('PHONEMES', "Phonemes", "Phoneme Expressions"),
               ),
        default='ARKIT')
    expression_presets = {
        'ARKIT': "arkit_expressions.face",
        'TONGUE': "tongue_expressions.face",
        'PHONEMES': "phoneme_expressions.face",
        'A2F': "a2f_46_expressions.face",
    }
    load_custom_path: BoolProperty(
        name="Load Custom Expressions",
        description="Load a custom expression set. (.face)",
        default=False,
        options={'SKIP_SAVE', },
    )
    load_method: EnumProperty(
        name="Load Method",
        items=(
            ('APPEND', "Append", "Append to existing ExpressionsList"),
            ('OVERWRITE', "Overwrite", "Overwrite existing ExpressionsList"),

        ),
        default='APPEND'
    )
    filepath: StringProperty(
        subtype="FILE_PATH",
        default='face'
    )
    filter_glob: StringProperty(
        default="*.face;",
        options={'HIDDEN'},
    )
    scale_method: EnumProperty(
        name='Scale Method',
        items=(
            ('AUTO', "Auto Scale", "Do automatically scale by matching the rig size to the scene"),
            ('OVERWRITE', "Manual Scale", "Manually overwrite scale of the action"),
        ),
        default='AUTO',
    )
    auto_scale_method: EnumProperty(
        name='Auto Scale Method',
        items=(
            ('GLOBAL', "XYZ", "Scale Pose Translations in XYZ (World Space)."),
            ('AVERAGE', "Average", "Scale Poses by an Average factor."),
        ),
        default='GLOBAL',
    )
    auto_scale_anime_eyes: BoolProperty(
        name="Scale For Anime Eyes",
        default=False,
        description="Scale all expressions down for Anime Eyes (flat eyes with pivots that lie inside the skull)",
        options={'SKIP_SAVE', }
    )
    new_action_scale: FloatVectorProperty(
        name="New Scale",
        default=(1.0, 1.0, 1.0),
    )
    auto_scale_eyes: BoolProperty(
        name="Scale Eye Dimensions",
        default=True
    )
    apply_existing_corrective_shape_keys: BoolProperty(
        name="Apply Corrective Shape Keys",
        description="Try to apply the existing corrective shape keys to the new expressions.",
        default=True,
    )
    is_version_one: BoolProperty(
        options={'SKIP_SAVE', },
    )
    custom_expressions_rig_type: EnumProperty(
        name='Rig Type',
        items=(
            ('RIGIFY', "Rigify", "Faceit default Rig (Rigify old)"),
            ('RIGIFY_NEW', "New Rigify", "The new Rigify Face Rig"),
        ),
        default='RIGIFY',
        options={'SKIP_SAVE', },
    )
    convert_animation_to_new_rigify: BoolProperty(
        name="Convert Animation to New Rigify",
        description="Convert the animation to the new Rigify Rig",
        default=False,
        options={'SKIP_SAVE', },
    )

    def __init__(self):
        self.corr_sk = False
        self.first_expression_set = False
        self.is_new_rigify_rig = False
        self.rig_type = 'FACEIT'

    @ classmethod
    def poll(cls, context):
        if context.mode not in ['POSE', 'OBJECT']:
            return False
        rig = futils.get_faceit_armature()
        if rig:
            if rig.hide_viewport is False:
                return True

    def invoke(self, context, event):
        self.filepath = "faceit_expressions.face"
        self.corr_sk = any([sk_name.startswith("faceit_cc_")
                            for sk_name in sk_utils.get_shape_key_names_from_objects()])
        rig = futils.get_faceit_armature()
        self.rig_type = futils.get_rig_type(rig)
        if self.rig_type == 'RIGIFY_NEW':
            self.is_new_rigify_rig = True
        self.first_expression_set = (len(context.scene.faceit_expression_list) <= 0)
        if self.load_custom_path:
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}
        else:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        if not self.is_version_one:
            if not self.load_custom_path:
                row = layout.row()
                row.prop(self, "expressions_type")
            if not self.first_expression_set:
                row = layout.row()
                row.label(text="Choose Append Method")
                row = layout.row()
                row.prop(self, "load_method", expand=True)
        row = layout.row()
        row.label(text="Choose Scale Method")
        row = layout.row()
        row.prop(self, "scale_method", expand=True)
        row = layout.row()
        if self.scale_method == 'OVERWRITE':
            row.prop(self, "new_action_scale")
        elif self.scale_method == 'AUTO':
            row.prop(self, "auto_scale_method", expand=True)
        row = layout.row()
        row.prop(self, "auto_scale_eyes", icon='CON_DISTLIMIT')
        if self.corr_sk:
            row = layout.row()
            row.prop(self, "apply_existing_corrective_shape_keys")
        if context.scene.faceit_use_eye_pivots:
            row = layout.row()
            row.label(text="Anime")
            row = layout.row()
            row.prop(self, "auto_scale_anime_eyes", icon='LIGHT_HEMI')
        if self.load_method == 'OVERWRITE' and not self.first_expression_set:
            box = layout.box()
            row = box.row()
            row.label(text="Warning", icon='ERROR')
            row = box.row()
            row.label(text="This will overwrite the existing expressions!")

    def execute(self, context):
        scene = context.scene
        save_frame = scene.frame_current
        state_dict = futils.save_scene_state(context)
        if self.load_custom_path:
            _filename, extension = os.path.splitext(self.filepath)
            if extension != ".face":
                self.report({'ERROR'}, "You need to provide a file of type .face")
                return {'CANCELLED'}
            if not os.path.isfile(self.filepath):
                self.report({'ERROR'}, f"The specified filepath does not exist: {os.path.realpath(self.filepath)}")
                return {'CANCELLED'}
            expressions_type = None
        else:
            expressions_type = self.expressions_type
        expression_list = scene.faceit_expression_list
        warnings = False
        if futils.get_object_mode_from_context_mode(context.mode) != 'OBJECT' and context.object is not None:
            bpy.ops.object.mode_set()
        rig = futils.get_faceit_armature()
        if not rig.animation_data:
            rig.animation_data_create()
        ow_action = bpy.data.actions.get("overwrite_shape_action")
        shape_action = bpy.data.actions.get("faceit_shape_action")
        if self.load_method == 'APPEND':
            if not expression_list:
                self.report(
                    {'INFO'},
                    "Could not append the expressions, because there are no shapes. Using Overwrite method instead")
                self.load_method = 'OVERWRITE'
            if not shape_action or not ow_action:
                self.report(
                    {'INFO'},
                    "Could not append the action, because no Action was found. Using Overwrite method instead")
                self.load_method = 'OVERWRITE'
        if self.load_method == 'OVERWRITE':
            expression_list.clear()
            if shape_action:
                bpy.data.actions.remove(shape_action)
                shape_action = None
            if ow_action:
                bpy.data.actions.remove(ow_action)
                ow_action = None
        # Reset all bone transforms!
        futils.set_active_object(rig.name)
        layer_state = rig.data.layers[:]
        for i, _ in enumerate(rig.data.layers):
            rig.data.layers[i] = True
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()
        # ------------------ Read New Expressions Data ------------------------
        # | - Load Expressions Data to temp action
        # | - Keyframes, Rig Dimensions, Rest Pose,
        # ---------------------------------------------------------------------
        new_shape_action = None
        if not self.load_custom_path:
            self.filepath = fdata.get_expression_presets(
                rig_type=self.rig_type) + self.expression_presets[expressions_type]
        if not os.path.isfile(self.filepath):
            self.report({'ERROR'}, f"The specified filepath does not exist: {os.path.realpath(self.filepath)}")
            return {'CANCELLED'}
        action_dict = {}
        eye_dimensions = []
        loaded_rig_type = 'FACEIT'
        with open(self.filepath, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                expression_data_loaded = data["expressions"]
                # import_rig_dimensions = data["action_scale"]
                rest_pose = data["rest_pose"]
                action_dict = data["action"]
                eye_dimensions = data.get("eye_dimensions")
                loaded_rig_type = data.get("rig_type", 'FACEIT')
        if loaded_rig_type == 'FACEIT' and self.is_new_rigify_rig:
            print("Converting old FaceIt Rig to new Rigify Rig")
            self.convert_animation_to_new_rigify = True
        new_shape_action = bpy.data.actions.new(name="temp")
        rig.animation_data.action = new_shape_action
        new_expression_count = len(expression_data_loaded.keys())
        zero_frames = set()
        new_frames = []
        for i in range(new_expression_count):
            frame = (i + 1) * 10
            new_frames.append(frame)
            zero_frames.update((frame + 1, frame - 9))
        zero_frames = sorted(list(zero_frames))
        start_time = time.time()
        missing_dps = []

        # In order to convert the rotation values to the expected rotation mode of the bone
        # we need to reconstruct the values from the data array.
        # The data array contains the rotation values separated by channels.
        for dp, data_per_array_index in action_dict.items():
            bone_name = a_utils.get_bone_name_from_data_path(dp)
            if self.convert_animation_to_new_rigify:
                new_name = fdata.get_rigify_bone_from_old_name(bone_name)
                dp = dp.replace(bone_name, new_name)
                bone_name = new_name
            if "influence" in dp:
                continue
            if bone_name not in rig.pose.bones:
                if bone_name not in missing_dps:
                    missing_dps.append(bone_name)
                continue
            # Get only the data path value
            data_path_from = a_utils.get_data_path_value(dp)
            channels = None
            if "rotation" in data_path_from:
                pose_bone = rig.pose.bones[bone_name]
                rot_mode_to = a_utils.get_rotation_mode(pose_bone)
                rotation_data_path_to = a_utils.get_data_path_from_rotation_mode(rot_mode_to)
                rot_mode_from = a_utils.get_rotation_mode_from_data_path_val(data_path_from)
                # Check if the rotation mode is already the expected rotation mode, nothing needs to be done
                if data_path_from == "rotation_euler":
                    channels = 3
                else:
                    # axis_angle and quaternion both have 4 channels.
                    channels = 4
                if rotation_data_path_to != data_path_from:
                    if rot_mode_to == 'EULER':
                        new_channels = 3
                    else:
                        new_channels = 4
                    # Replace the data path with the expected rotation mode
                    dp = dp.replace(data_path_from, rotation_data_path_to)
                    # Get the number of channels for the old rotation mode and new rotation_mode
                    # Reconstruct full rotation values based on the individual channels in the data array
                    # and convert them to the expected rotation mode
                    # currently the data is stored like this: {i: [(frame, value), (frame, value), ...]}
                    # new format (frames_dict) for rotation mode conversion {frame: {i:[value, value, ...]}}
                    frames_dict = {}
                    for i, frame_value_list in data_per_array_index.items():
                        i = int(i)
                        for frame, value in frame_value_list:
                            if frame not in frames_dict:
                                frames_dict[frame] = {}
                            frames_dict[frame][i] = value
                    # Convert the rotation values to the expected rotation mode and populate into the data_dict
                    data_per_array_index = {}
                    for frame, value_dict in frames_dict.items():
                        rot_value = []
                        for i in range(channels):
                            val = value_dict.get(i)
                            if val:
                                rot_value.append(val)
                            else:
                                # Reconstruct missing values (default value for this channel)
                                if i == 0 and data_path_from == 'rotation_quaternion':
                                    rot_value.append(1)
                                    # axis angle default (0.0, 0.0, 1.0, 0.0)
                                else:
                                    rot_value.append(0)
                        rot_value = a_utils.get_value_as_rotation(rot_mode_from, rot_value)  # Euler(rot_value)
                        new_rot_value = a_utils.convert_rotation_values(rot_value, rot_mode_from, rot_mode_to)[:]
                        # Reconstruct the data dict with new rotation mode / values
                        for i, value in enumerate(new_rot_value):
                            i = str(i)
                            if i not in data_per_array_index:
                                data_per_array_index[i] = []
                            data_per_array_index[i].append([frame, value])
                    channels = new_channels
            elif any(x in dp for x in ["scale", "location"]):
                channels = 3
            else:
                channels = 1
            for i in range(channels):
                data = data_per_array_index.get(str(i))
                fc = new_shape_action.fcurves.find(data_path=dp, index=i)
                if fc:
                    print("FCurve already exists! Skipping: {}".format(fc.data_path))
                    break
                fc = new_shape_action.fcurves.new(data_path=dp, index=i)
                if data:
                    kf_data = np.array(data)
                else:
                    kf_data = np.empty(2)
                # Adding Zero Keyframes for all rest poses inbetween expressions!
                base_value = 0
                if "scale" in dp:
                    base_value = 1
                elif "rotation_quaternion" in dp and i == 0:
                    base_value = 1
                kf_data_base = np.array([(f, base_value) for f in zero_frames])
                if kf_data.ndim == 1:
                    kf_data = kf_data_base
                else:
                    kf_data = np.concatenate((kf_data, kf_data_base), axis=0)
                kf_data = kf_data[kf_data[:, 0].argsort()]
                fc_dr_utils.populate_keyframe_points_from_np_array(fc, kf_data, add=True)
        for fc in new_shape_action.fcurves:
            if 'jaw_master_mouth' in fc.data_path:
                print(fc.data_path)
            for kf in fc.keyframe_points:
                kf.interpolation = 'LINEAR'
        print(f"Added new Keyframes in {round(time.time() - start_time, 2)}")
        for bone_name in missing_dps:
            if self.rig_type == 'FACEIT':
                self.report(
                    {'WARNING'},
                    f"An Fcurve has been loaded for the bone {bone_name} which is missing in the Faceit Rig. Regenerate the Rig!")
            else:
                self.report(
                    {'WARNING'},
                    f"An Fcurve has been loaded for the bone {bone_name} which is missing in the Rig {rig.name}.")
            warnings = True
        # ------------------------- SCALE ACTION ----------------------------------
        # | - Scale Action to new rig dimensions.
        # | - Eyelid is calculated and skaled separately.
        # -------------------------------------------------------------------------
        skip_lid_bones = {
            "lid.T.L.003",
            "lid.T.L.002",
            "lid.T.L.001",
            "lid.B.L.001",
            "lid.B.L.002",
            "lid.B.L.003",
            "lid.B.L",
            "lid.T.L",
            "lid.T.R.003",
            "lid.T.R.002",
            "lid.T.R.001",
            "lid.B.R.001",
            "lid.B.R.002",
            "lid.B.R.003",
            "lid.B.R",
            "lid.T.R",
        }
        skip_double_constraint = {
            "nose.005",
            "chin.002",
            "nose.003",
        }
        skip_scale_bones = skip_double_constraint
        if eye_dimensions and self.auto_scale_eyes:
            skip_scale_bones.update(skip_lid_bones)
        # get control bones on the face only (no eye target controllers)
        skip_dimension_check = {"eye.L", "eye.R", "eyes", "eye_common"}
        # Relevant / animated bones for scaling
        facial_control_bones = {pb.name for pb in rig.pose.bones if pb.name in fdata.FACEIT_CTRL_BONES}
        # Dimension relevant control bones that are present in rig and in the imported data
        bone_dimensions_check = facial_control_bones.intersection(rest_pose) - skip_dimension_check

        def get_import_rig_dimensions(pose_bones):
            '''Get the dimensions of the imported rest pose data'''
            x_values = []
            y_values = []
            z_values = []
            # Return the bones that are found for comparison!
            # for _, values in rest_pose.items():
            for pb in pose_bones:
                values = rest_pose.get(pb.name)
                x_values.append(values[0])
                y_values.append(values[1])
                z_values.append(values[2])
            dim_x = max(x_values) - min(x_values)
            dim_y = max(y_values) - min(y_values)
            dim_z = max(z_values) - min(z_values)
            return [dim_x, dim_y, dim_z]

        def get_rig_dimensions(pose_bones):
            '''Get the dimensions for all faceit control bones'''
            x_values = []
            y_values = []
            z_values = []
            for pb in pose_bones:
                x_values.append(pb.bone.matrix_local.translation[0])
                y_values.append(pb.bone.matrix_local.translation[1])
                z_values.append(pb.bone.matrix_local.translation[2])
            dim_x = max(x_values) - min(x_values)
            dim_y = max(y_values) - min(y_values)
            dim_z = max(z_values) - min(z_values)
            return [dim_x, dim_y, dim_z]

        action_scale = [1.0, ] * 3
        scale_bones = [pb for pb in rig.pose.bones if pb.name in (facial_control_bones - skip_scale_bones)]
        # scale_bones = [pb for pb in facial_control_bones if pb.name not in skip_scale_bones]
        if self.scale_method == 'AUTO':
            # get bones present in both current pose and imported pose and compare dimensions
            bone_dimensions_check = [pb for pb in rig.pose.bones if pb.name in bone_dimensions_check]
            import_rig_dimensions = get_import_rig_dimensions(bone_dimensions_check)
            rig_dim = get_rig_dimensions(bone_dimensions_check)
            # print(f"Rig Dimensions: {rig_dim}")
            # print(f"Import Rig Dimensions: {import_rig_dimensions}")
            for i in range(3):
                action_scale[i] = rig_dim[i] / import_rig_dimensions[i]
            if not all(x == 1 for x in action_scale):
                if self.auto_scale_method == 'GLOBAL':
                    a_utils.scale_poses_to_new_dimensions_slow(
                        rig,
                        pose_bones=scale_bones,
                        scale=action_scale,
                        active_action=new_shape_action,
                        frames=new_frames
                    )
                else:
                    a_utils.scale_action_to_rig(
                        new_shape_action,
                        action_scale,
                        filter_skip=skip_lid_bones,
                        frames=new_frames
                    )
        elif self.scale_method == 'OVERWRITE':
            action_scale = self.new_action_scale
            if not all(x == 1 for x in action_scale):
                a_utils.scale_poses_to_new_dimensions_slow(
                    rig,
                    pose_bones=scale_bones,
                    scale=action_scale,
                    active_action=new_shape_action,
                    frames=new_frames
                )
        # Scale eyelid expressions to new dimensions!
        if eye_dimensions and self.auto_scale_eyes:
            a_utils.scale_eye_animation(rig, *eye_dimensions, action=new_shape_action)
        if self.auto_scale_anime_eyes:
            a_utils.scale_eye_look_animation(rig, scale_factor=0.45, action=new_shape_action)
        # check if the expressions are generated with the new rigify rig, if so no need to scale.
        if self.is_new_rigify_rig and self.convert_animation_to_new_rigify:  # and self.convert_to_new_rigify_rig:
            a_utils.scale_eye_look_animation(rig, scale_factor=0.25, action=new_shape_action)

        # ------------------------ Append the keyframes -------------------------------
        # | - Append the Keyframes
        # | - Activate the Shape Action
        # -------------------------------------------------------------------------
        if self.load_method == 'OVERWRITE':
            shape_action = new_shape_action
            shape_action.name = "faceit_shape_action"
        else:
            # Apply frame offset to the fcurve data and apply to existing shape action
            frame_offset = int(futils.get_action_frame_range(ow_action)[1] - 1)
            for import_fc in new_shape_action.fcurves:
                kf_data = fc_dr_utils.kf_data_to_numpy_array(import_fc)
                kf_data[:, 0] += frame_offset
                dp = import_fc.data_path
                a_index = import_fc.array_index
                if shape_action:
                    fc = fc_dr_utils.get_fcurve_from_bpy_struct(shape_action.fcurves, dp=dp, array_index=a_index)
                    fc_dr_utils.populate_keyframe_points_from_np_array(fc, kf_data, add=True)
                else:
                    self.report({'WARNING'}, "Could not find the Faceit Shape Action. Failed to append")
                    warnings = True
                if ow_action:
                    fc = fc_dr_utils.get_fcurve_from_bpy_struct(ow_action.fcurves, dp=dp, array_index=a_index)
                    fc_dr_utils.populate_keyframe_points_from_np_array(fc, kf_data, add=True)
                else:
                    self.report({'WARNING'}, "Could not find the Faceit Overwrite Action. Failed to append")
                    warnings = True
            bpy.data.actions.remove(new_shape_action)
        if self.load_method == 'OVERWRITE':
            ow_action = a_utils.create_overwrite_animation(rig)
        if ow_action:
            rig.animation_data.action = ow_action
            ow_action.use_fake_user = True
        if shape_action:
            shape_action.use_fake_user = True
        # ------------------------ Load Expressions -------------------------------
        # | - Load Expressions Items to list.
        # -------------------------------------------------------------------------
        for expression_name, expression_data in expression_data_loaded.items():
            mirror_name = expression_data.get("mirror_name", "")
            side = expression_data.get("side") or "N"
            procedural = expression_data.get("procedural", 'NONE')
            # print(f"adding {expression_name}, side:{side}, mirror:{mirror_name}, procedural:{procedural}")
            bpy.ops.faceit.add_expression_item(
                'EXEC_DEFAULT',
                expression_name=expression_name,
                side=side,
                mirror_name_overwrite=mirror_name,
                procedural=procedural,
                is_new_rigify_rig=self.is_new_rigify_rig
            )
        if expressions_type == 'ARKIT':  # and not self.load_custom_path:
            bpy.ops.faceit.procedural_mouth_close(
                'INVOKE_DEFAULT',
                jaw_open_expression="jawOpen",
                mouth_close_expression="mouthClose",
                is_new_rigify_rig=self.is_new_rigify_rig
            )
        if expressions_type == 'A2F':  # and not self.load_custom_path:
            bpy.ops.faceit.procedural_mouth_close(
                'INVOKE_DEFAULT',
                jaw_open_expression="jawDrop",
                mouth_close_expression="jawDropLipTowards",
                is_new_rigify_rig=self.is_new_rigify_rig
            )
        bpy.ops.faceit.force_zero_frames('EXEC_DEFAULT')
        rig.data.layers = layer_state[:]
        if warnings:
            self.report(
                {'WARNING'},
                "Operator finished with Warnings. Take a look at the console output for more information.")
        else:
            self.report({'INFO'}, "New Expressions.")
        if self.apply_existing_corrective_shape_keys:
            reevaluate_corrective_shape_keys(expression_list, futils.get_faceit_objects_list())
        else:
            clear_all_corrective_shape_keys(futils.get_faceit_objects_list(), expression_list=expression_list)
        scene.frame_start, scene.frame_end = (int(x) for x in futils.get_action_frame_range(ow_action))
        futils.restore_scene_state(context, state_dict)
        if self.first_expression_set:
            scene.tool_settings.use_keyframe_insert_auto = True
        scene.frame_current = save_frame
        return {'FINISHED'}


class FACEIT_OT_ForceZeroFrames(bpy.types.Operator):
    ''' Adds Zero Keyframes for all rest poses inbetween expressions! Effects pose bones and constraints.'''
    bl_idname = "faceit.force_zero_frames"
    bl_label = "Force Zero Frames"
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    @ classmethod
    def poll(cls, context):
        scene = context.scene
        rig = futils.get_faceit_armature()
        if rig and scene.faceit_expression_list and context.mode in ['OBJECT', 'POSE']:
            if rig.animation_data:
                if rig.animation_data.action:
                    return True
        return False

    def execute(self, context):
        state_dict = futils.save_scene_state(context)

        scene = context.scene
        rig = futils.get_faceit_armature()

        scene = context.scene
        save_frame = scene.frame_current
        expression_list = scene.faceit_expression_list

        mode_save = futils.get_object_mode_from_context_mode(context.mode)
        if context.active_object != rig:
            if mode_save != 'OBJECT' and context.object is not None:
                bpy.ops.object.mode_set()
            futils.clear_object_selection()
            futils.set_active_object(rig.name)

        layer_state = rig.data.layers[:]
        for i, _ in enumerate(rig.data.layers):
            rig.data.layers[i] = True

        bpy.ops.object.mode_set(mode='POSE')

        bpy.ops.pose.select_all(action='DESELECT')

        zero_frames = set()

        for exp in expression_list:
            zero_frames.update((exp.frame + 1, exp.frame - 9))

        zero_frames = sorted(list(zero_frames))

        zero_ref_frame = zero_frames[0]
        scene.frame_set(zero_ref_frame)

        for pb in rig.pose.bones:
            layers = pb.bone.layers
            if layers[0] or layers[1] or layers[2]:
                pb.bone.select = True
            else:
                pb.bone.select = False

        bpy.ops.pose.transforms_clear()
        bpy.ops.anim.keyframe_insert(type="Location")
        bpy.ops.anim.keyframe_insert(type="Rotation")
        bpy.ops.anim.keyframe_insert(type="Scaling")

        bpy.ops.object.mode_set()

        bpy.ops.object.mode_set(mode='POSE')

        for fc in rig.animation_data.action.fcurves:
            if "constraints" in fc.data_path or "influence" in fc.data_path:
                continue
            kf_zero_value = 0

            if "scale" in fc.data_path:
                kf_zero_value = 1
            elif "rotation_quaternion" in fc.data_path and fc.array_index == 0:
                kf_zero_value = 1

            # for f in sorted(zero_frames+new_frames):
            for f in zero_frames:
                fc.keyframe_points.insert(f, kf_zero_value, options={'FAST'})

            fc.update()
        scene.frame_current = save_frame
        bpy.ops.pose.select_all(action='DESELECT')
        rig.data.layers = layer_state[:]
        futils.restore_scene_state(context, state_dict)

        return {'FINISHED'}

# START ####################### VERSION 2 ONLY #######################


class FACEIT_OT_ExportExpressionsToJson(bpy.types.Operator, ExportHelper):
    ''' Export the current Expression file to json format '''
    bl_idname = "faceit.export_expressions"
    bl_label = "Export Expressions"
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    filepath: StringProperty(
        subtype="FILE_PATH",
        default="faceit_expressions"
    )
    filter_glob: StringProperty(
        default="*.face;",
        options={'HIDDEN'},
    )
    filename_ext = ".face"
    adjust_scale = True
    rig_type = 'FACEIT'

    @ classmethod
    def poll(cls, context):
        scene = context.scene
        rig = futils.get_faceit_armature()
        if rig and scene.faceit_expression_list:
            if rig.animation_data:
                if rig.animation_data.action:
                    return True

    def execute(self, context):
        scene = context.scene
        rig = futils.get_faceit_armature()
        # value in 'FACEIT', 'RIGIFY', 'RIGIFY_NEW'
        rig_type = futils.get_rig_type(rig)
        scene = context.scene
        save_frame = scene.frame_current
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False
        expression_list = scene.faceit_expression_list
        mode_save = futils.get_object_mode_from_context_mode(context.mode)
        if context.active_object != rig:
            if mode_save != 'OBJECT' and context.object is not None:
                bpy.ops.object.mode_set()
            futils.clear_object_selection()
            futils.set_active_object(rig.name)
        layer_state = rig.data.layers[:]
        for i, _ in enumerate(rig.data.layers):
            rig.data.layers[i] = True
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.select_all(action='DESELECT')
        try:
            bpy.ops.object.mode_set(mode=mode_save)
        except TypeError:
            print(f"Can't activate mode {mode_save} from current context")
        rig.data.layers = layer_state[:]
        action_scale = list(rig.dimensions.copy())
        eye_dim_L, eye_dim_R = a_utils.get_eye_dimensions(rig)
        action = rig.animation_data.action
        data = {}
        expression_list_data = {}
        expression_list = scene.faceit_expression_list
        for exp in expression_list:
            procedural = getattr(exp, "procedural", 'NONE')
            if exp.name in ("eyeBlinkLeft", "eyeBlinkRight") and procedural == 'NONE':
                procedural = 'EYEBLINKS'
            expression_list_data[exp.name] = {
                'mirror_name': exp.mirror_name,
                'side': exp.side,
                'procedural': procedural
            }
        rest_pose_dict = {}
        for pb in rig.pose.bones:
            layers = pb.bone.layers
            if layers[0] is True or layers[1] is True or layers[2] is True:
                rest_pose_dict[pb.name] = list(pb.bone.matrix_local.translation)
        action_dict = {}
        remove_zero_keyframes = True
        remove_zero_poses = True
        for fc in action.fcurves:
            dp = fc.data_path
            array_index = fc.array_index
            # skip non-control bones
            if any(x in dp for x in ["DEF-", "MCH-", "ORG-"]):
                continue
            # Skip constraint animation
            if "influence" in fc.data_path:
                continue
            kf_data = fc_dr_utils.kf_data_to_numpy_array(fc)
            if "mouth_lock" in dp:
                print("skipping mouth lock")
                pass
            else:
                if remove_zero_poses:
                    kf_data = kf_data[np.logical_not(kf_data[:, 0] % 10 != 0)]
                if remove_zero_keyframes:
                    if "scale" in fc.data_path or "rotation_quaternion" in fc.data_path and array_index == 0:
                        kf_data = kf_data[np.logical_not(kf_data[:, 1] == 1.0)]
                    else:
                        # delete zero values
                        kf_data = kf_data[np.logical_not(kf_data[:, 1] == 0.0)]
            kf_anim_data = kf_data.tolist()
            if not kf_anim_data:
                continue
            dp_dict = action_dict.get(dp)
            if dp_dict:
                dp_dict[array_index] = kf_anim_data
            else:
                action_dict[dp] = {array_index: kf_anim_data}
        data["rig_type"] = rig_type
        data["action_scale"] = list(action_scale)
        data["eye_dimensions"] = [eye_dim_L, eye_dim_R]
        data["expressions"] = expression_list_data
        data["rest_pose"] = rest_pose_dict
        data["action"] = action_dict
        if not self.filepath.endswith(".face"):
            self.filepath += ".face"
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        scene.frame_current = save_frame
        scene.tool_settings.use_keyframe_insert_auto = auto_key

        return {'FINISHED'}


class FACEIT_OT_ClearFaceitExpressions(bpy.types.Operator):
    '''Clear all Faceit Expressions'''
    bl_idname = "faceit.clear_faceit_expressions"
    bl_label = "Clear Expressions"
    bl_options = {'UNDO', 'INTERNAL'}

    keep_corrective_shape_keys: BoolProperty(
        name="Keep Corrective Shape Keys",
        description="Keep all corrective Shape Keys and try to apply them on a new expression.",
        default=True,
    )

    corr_sk = True

    @ classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        self.corr_sk = any([sk_name.startswith("faceit_cc_")
                           for sk_name in sk_utils.get_shape_key_names_from_objects()])

        if self.corr_sk:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def execute(self, context):
        scene = context.scene
        scene.faceit_expression_list.clear()
        scene.faceit_expression_list_index = -1
        shape_action = bpy.data.actions.get("faceit_shape_action")
        ow_action = bpy.data.actions.get("overwrite_shape_action")
        if shape_action:
            bpy.data.actions.remove(shape_action)
        if ow_action:
            bpy.data.actions.remove(ow_action)

        rig = futils.get_faceit_armature()

        if rig:
            if rig.animation_data:
                rig.animation_data.action = None

            for b in rig.pose.bones:
                reset_pb(b)
        if self.corr_sk:
            faceit_objects = futils.get_faceit_objects_list()

            for obj in faceit_objects:

                if sk_utils.has_shape_keys(obj):
                    for sk in obj.data.shape_keys.key_blocks:
                        if sk.name.startswith("faceit_cc_"):
                            # mute corrective shapes!
                            if self.keep_corrective_shape_keys:
                                sk.mute = True
                                scene.faceit_corrective_sk_restorable = True
                            else:
                                obj.shape_key_remove(sk)
                                scene.faceit_corrective_sk_restorable = False

                    if obj.data.shape_keys.animation_data:
                        a = obj.data.shape_keys.animation_data.action
                        if a:
                            if a.name == CORRECTIVE_SK_ACTION_NAME:
                                obj.data.shape_keys.animation_data.action = None

                    if len(obj.data.shape_keys.key_blocks) == 1:
                        obj.shape_key_clear()

        a_utils.restore_constraints_to_default_values(rig)

        return {'FINISHED'}


class FACEIT_OT_RemoveExpressionItem(bpy.types.Operator):
    '''Remove the selected Character Geometry from Registration.'''
    bl_idname = "faceit.remove_expression_item"
    bl_label = "Remove Expression"
    bl_options = {'UNDO', 'INTERNAL'}

    remove_item: bpy.props.StringProperty(
        default="",
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    @ classmethod
    def poll(cls, context):
        idx = context.scene.faceit_expression_list_index

        if idx >= 0 and idx < len(context.scene.faceit_expression_list):
            return True

    def execute(self, context):

        scene = context.scene
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False

        expression_list = scene.faceit_expression_list
        expression_list_index = scene.faceit_expression_list_index

        ow_action = bpy.data.actions.get("overwrite_shape_action")
        sh_action = bpy.data.actions.get("faceit_shape_action")

        if len(expression_list) <= 1:
            bpy.ops.faceit.clear_faceit_expressions()
            scene.frame_start, scene.frame_end = 1, 250
            return {'FINISHED'}

        def _remove_faceit_item(item):

            item_index = expression_list.find(item.name)

            frame = item.frame

            actions = [ow_action, sh_action]
            for action in actions:
                if action:
                    for curve in action.fcurves:
                        for key in curve.keyframe_points:
                            if key.co[0] == frame:
                                curve.keyframe_points.remove(key, fast=True)
                    for curve in action.fcurves:
                        for key in curve.keyframe_points:
                            if key.co[0] > frame:
                                key.co[0] -= 10

            cc_action = bpy.data.actions.get(CORRECTIVE_SK_ACTION_NAME)
            if cc_action:
                for curve in cc_action.fcurves:
                    for key in curve.keyframe_points:
                        if key.co[0] == frame:
                            curve.keyframe_points.remove(key, fast=True)
                for curve in cc_action.fcurves:
                    for key in curve.keyframe_points:
                        if key.co[0] > frame:
                            key.co[0] -= 10

            expression_list.remove(item_index)
            for item in expression_list:
                if item.frame > frame:
                    item.frame -= 10

        # remove from face objects
        if len(expression_list) > 0:
            if self.remove_item:
                item = expression_list[self.remove_item]
            else:
                item = expression_list[expression_list_index]
            _remove_faceit_item(item)

        expression_count = len(expression_list)

        if expression_list_index >= expression_count:
            scene.faceit_expression_list_index = expression_count - 1

        scene.tool_settings.use_keyframe_insert_auto = auto_key
        if ow_action:
            scene.frame_start, scene.frame_end = (int(x) for x in futils.get_action_frame_range(ow_action))

        return {'FINISHED'}


# END ######################### VERSION 2 ONLY #######################


class FACEIT_OT_PoseAmplify(bpy.types.Operator):
    '''Relax Pose of active Expression'''
    bl_idname = "faceit.pose_amplify"
    bl_label = "Amplify Pose"
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    expression_index: IntProperty(
        name='Expression to effect',
        options={'HIDDEN', 'SKIP_SAVE'},
        default=-1,
    )

    percentage: FloatProperty(
        name="Percentage",
        default=1.0,
        options={'SKIP_SAVE'},
        # subtype='',
    )

    selected_bones_only: BoolProperty(
        name="Selected Bones only",
        description="Amplify only the selected pose bones, instead of all posed bones.",
        default=False,
        options={'SKIP_SAVE'},
    )

    @ classmethod
    def poll(cls, context):
        scene = context.scene
        rig = futils.get_faceit_armature()
        if rig and scene.faceit_expression_list:
            if rig.animation_data:
                if rig.animation_data.action:
                    return True

    def invoke(self, context, event):
        wm = context.window_manager
        if self.expression_index != -1:
            return wm.invoke_props_popup(self, event)
        else:
            return wm.invoke_props_dialog(self)

    def execute(self, context):

        scene = context.scene
        rig = futils.get_faceit_armature()
        action = rig.animation_data.action

        # effect all expressions if frame -1
        frame = -1
        # Effect specific expression:
        if self.expression_index != -1:
            scene.faceit_expression_list_index = self.expression_index
            expression_list = scene.faceit_expression_list
            expression = expression_list[self.expression_index]
            frame = expression.frame

        if self.selected_bones_only:
            selected_pbones = []
            for pb in rig.pose.bones:
                if pb.bone.select is True:
                    selected_pbones.append(pb.name)
            a_utils.amplify_pose(action, filter_pose_bone_names=selected_pbones,
                                 frame=frame, scale_factor=self.percentage)
        else:
            a_utils.amplify_pose(action, frame=frame, scale_factor=self.percentage)

        self.report({'INFO'}, f"scaled by {self.percentage}")

        return {'FINISHED'}


class FACEIT_OT_GoToFrame(bpy.types.Operator):
    '''Snap Timeline Cursor to the nearest Expression'''
    bl_idname = "faceit.set_timeline"
    bl_label = "Snap Timeline Cursor to Expression"
    bl_options = {'UNDO', 'INTERNAL'}

    @ classmethod
    def poll(cls, context):
        scene = context.scene
        current_expression = scene.faceit_expression_list[scene.faceit_expression_list_index]
        if futils.get_faceit_armature() and current_expression.frame != scene.frame_current:
            return True

    def execute(self, context):

        a_utils.set_pose_from_timeline(context)

        return {'FINISHED'}


class FACEIT_OT_ResetExpression(bpy.types.Operator):
    '''Reset Pose to the originally generated Pose'''
    bl_idname = "faceit.reset_expression"
    bl_label = "Reset Expression"
    bl_options = {'UNDO', 'INTERNAL'}

    remove_corrective_shape_keys: bpy.props.BoolProperty(
        name="Remove Corrective Shapes",
        description="Removes the corrective Shape Keys.",
        default=True,
    )

    expression_to_reset: bpy.props.StringProperty(
        name="Expression to Reset",
        default="ALL"
    )

    selected_bones_only: BoolProperty(
        name="Selected Bones only",
        description="Amplify only the selected pose bones, instead of all posed bones.",
        default=False,
    )

    @ classmethod
    def poll(cls, context):
        rig = futils.get_faceit_armature()
        if rig:
            return rig.hide_viewport is False

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        if context.scene.faceit_use_corrective_shapes:
            if self.expression_to_reset == "ALL":
                row.prop(self, "remove_corrective_shape_keys", text="Remove all Corrective Shape Keys", icon='TRASH')
            elif any(["faceit_cc_" + self.expression_to_reset in sk_utils.get_shape_key_names_from_objects()]):
                row.prop(self, "remove_corrective_shape_keys", text="Remove Corrective Shape Key?", icon='TRASH')
        row = layout.row()
        row.prop(self, "selected_bones_only", text="Selected Bones only", icon='BONE_DATA')

    def execute(self, context):
        state_dict = futils.save_scene_state(context)

        shape_action = bpy.data.actions.get("faceit_shape_action")
        ow_action = bpy.data.actions.get("overwrite_shape_action")

        scene = context.scene
        rig = futils.get_faceit_armature()
        if not rig:
            self.report({'WARNING'}, "The Armature could not be found. Cancelled")
            return {'CANCELLED'}

        if context.active_object != rig:
            if futils.get_object_mode_from_context_mode(context.mode) != 'OBJECT' and context.object is not None:
                bpy.ops.object.mode_set()
            futils.clear_object_selection()
            futils.set_active_object(rig.name)

        expression_list = scene.faceit_expression_list
        curr_expression = scene.faceit_expression_list_index

        if self.expression_to_reset == "ALL":
            expressions_operate = expression_list
            if self.remove_corrective_shape_keys:
                clear_all_corrective_shape_keys(
                    futils.get_faceit_objects_list(),
                    expression_list=expression_list,
                )
        else:
            expressions_operate = [expression_list[self.expression_to_reset]]
            if self.remove_corrective_shape_keys:
                remove_corrective_shape_key(
                    expression_list, futils.get_faceit_objects_list(),
                    expression_name=self.expression_to_reset
                )
        selected_pbones = []
        if self.selected_bones_only:
            for pb in rig.pose.bones:
                if pb.bone.select is True:
                    selected_pbones.append(pb.name)
        for exp in expressions_operate:
            frame = exp.frame
            a_utils.reset_key_frame(action=ow_action, filter_pose_bone_names=selected_pbones,
                                    backup_action=shape_action, frame=frame)

        scene.faceit_expression_list_index = curr_expression

        futils.restore_scene_state(context, state_dict)
        # if self.remove_corrective_shape_keys:
        #     try:
        #         bpy.ops.object.mode_set()
        #     except:
        #         pass
        return {'FINISHED'}


class FACEIT_OT_MirrorOverwriteAnimation(bpy.types.Operator):
    '''Mirror the selected Expression to the opposite side (onyl L and R expressions)'''
    bl_idname = "faceit.mirror_overwrite"
    bl_label = "Mirror Expression"
    bl_options = {'UNDO', 'INTERNAL', 'REGISTER'}

    expression_to_mirror: bpy.props.StringProperty(
        name="Expression to Mirror",
        default="ACTIVE",
    )

    @ classmethod
    def poll(cls, context):
        rig = futils.get_faceit_armature()
        if rig is not None:
            if rig.hide_viewport is False:
                return True

    def execute(self, context):
        # create additive or overwrite animation
        scene = context.scene
        state_dict = futils.save_scene_state(context)

        rig = futils.get_faceit_armature()
        mirror_corrective_sk = scene.faceit_try_mirror_corrective_shapes
        if mirror_corrective_sk:
            faceit_objects = futils.get_faceit_objects_list()
            if scene.faceit_corrective_sk_mirror_affect_only_selected_objects:
                mirror_objects = context.selected_objects
                if not mirror_objects:
                    mirror_corrective_sk = False
                mirror_objects = (obj for obj in mirror_objects if obj in faceit_objects)
            else:
                mirror_objects = faceit_objects

        if context.object != rig:
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set()
            futils.clear_object_selection()
            futils.set_active_object(rig.name)

        if context.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        expression_list = scene.faceit_expression_list

        if self.expression_to_mirror == "ALL":
            expressions_to_mirror = expression_list
        else:
            expressions_to_mirror = [expression_list[self.expression_to_mirror]]

        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = True

        layer_state = rig.data.layers[:]
        for i, _ in enumerate(rig.data.layers):
            rig.data.layers[i] = True
        for exp in expressions_to_mirror:

            scene.frame_set(exp.frame)

            if exp.mirror_name:
                mirror_expression_idx = expression_list.find(exp.mirror_name)
                if mirror_expression_idx == -1:
                    self.report({'WARNING'}, f"The expression {exp.mirror_name} could not be found")
                    continue

                mirror_expression = expression_list[mirror_expression_idx]

                bpy.ops.pose.reveal(select=False)
                bpy.ops.pose.select_all(action='SELECT')

                bpy.ops.pose.copy()

                scene.frame_set(mirror_expression.frame)

                bpy.ops.pose.paste(flipped=True)

                bpy.ops.pose.select_all(action='DESELECT')

                scene.faceit_expression_list_index = mirror_expression_idx

        rig.data.layers = layer_state[:]

        scene.tool_settings.use_keyframe_insert_auto = auto_key

        bpy.ops.object.mode_set(mode='OBJECT')

        if mirror_corrective_sk:

            rig.data.pose_position = 'REST'
            warning_key_words = ["Warning: ", "failed"]

            action = bpy.data.actions.get(CORRECTIVE_SK_ACTION_NAME)
            for exp in expressions_to_mirror:
                if exp.mirror_name:
                    # Try to Mirror Shape Keys
                    # mirror_expression = expression_list[exp.mirror_name]
                    mirror_expression = expression_list.get(exp.mirror_name)
                    if not mirror_expression:
                        self.report({'WARNING'}, f"The expression {exp.mirror_name} could not be found")
                        continue

                    if action:
                        mirror_method = scene.faceit_corrective_sk_mirror_method

                        for obj in mirror_objects:

                            if sk_utils.has_shape_keys(obj):

                                futils.clear_object_selection()
                                futils.set_active_object(obj.name)

                                futils.set_hide_obj(obj, False)

                                shape_keys = obj.data.shape_keys.key_blocks

                                for ob_exp in expressions_to_mirror:

                                    sk_name = "faceit_cc_" + ob_exp.name

                                    sk = obj.data.shape_keys.key_blocks.get(sk_name)

                                    if sk:
                                        sk_mirror_name = "faceit_cc_" + mirror_expression.name
                                        sk_mirror = shape_keys.get(sk_mirror_name)
                                        if sk_mirror:
                                            obj.shape_key_remove(sk_mirror)
                                        sk_mirror = obj.shape_key_add(name=sk_mirror_name, from_mix=False)
                                        obj.active_shape_key_index = len(shape_keys) - 1

                                        mirror_expression.corr_shape_key = True
                                        frame = mirror_expression.frame

                                        sk_mirror.value = 0
                                        sk_mirror.keyframe_insert(data_path="value", frame=frame - 9)
                                        sk_mirror.keyframe_insert(data_path="value", frame=frame + 1)
                                        sk_mirror.value = 1
                                        sk_mirror.keyframe_insert(data_path="value", frame=frame)

                                        if mirror_method == 'FORCE':
                                            mirror_shape_key(obj, 0, sk, sk_mirror)
                                        else:
                                            bpy.ops.object.mode_set(mode='EDIT')
                                            bpy.ops.mesh.select_all(action='SELECT')
                                            bpy.ops.mesh.blend_from_shape(shape=sk.name, blend=1.0, add=False)
                                            bpy.ops.object.mode_set(mode='OBJECT')

                                            _stdout_warning = ''

                                            stdout = io.StringIO()

                                            with redirect_stdout(stdout):

                                                if scene.faceit_corrective_sk_mirror_method == 'NORMAL':
                                                    bpy.ops.object.shape_key_mirror(
                                                        use_topology=False)
                                                else:
                                                    bpy.ops.object.shape_key_mirror(
                                                        use_topology=True)

                                            stdout.seek(0)
                                            _stdout_warning = stdout.read()
                                            del stdout

                                            if all(w in _stdout_warning for w in warning_key_words):
                                                self.report(
                                                    {'WARNING'},
                                                    f"{_stdout_warning.rstrip()}! Try another Mirror Method."
                                                )
            rig.data.pose_position = 'POSE'

        print('Mirror Done!')

        if context.preferences.edit.use_visual_keying:
            self.report({'WARNING'}, "Visual Keying is enabled. Please disable it if mirroring doesn't work as expected.")

        futils.restore_scene_state(context, state_dict)
        return {'FINISHED'}


def mirror_shape_key(obj, axis, mirror_from_shape, mirror_to_shape, force=False):
    '''Mirror Shape Key across axis '''

    me = obj.data
    size = len(me.vertices)
    kd = kdtree.KDTree(size)
    for i, v in enumerate(me.vertices):
        kd.insert(v.co, i)
    kd.balance()

    indices_mirrored = []
    for v in obj.data.vertices:
        mirror_co = v.co.copy()
        mirror_co[axis] = mirror_co[axis] * -1
        kd_res = kd.find(mirror_co)
        indices_mirrored.append(kd_res[1])

    if indices_mirrored:
        new_data = [v.co.copy() for v in me.vertices]
        for i, _data in enumerate(mirror_from_shape.data):
            new_co = mirror_from_shape.data[indices_mirrored[i]].co.copy()
            new_co[axis] = new_co[axis] * -1
            new_data[i] = new_co

    for i, co in enumerate(new_data):
        mirror_to_shape.data[i].co = co


class FACEIT_OT_ProceduralEyeBlinks(bpy.types.Operator):
    '''Procedural eye blinking expressions'''
    bl_idname = "faceit.procedural_eye_blinks"
    bl_label = "Procedural Eye Blinks"
    bl_options = {'UNDO', 'INTERNAL'}

    expression_index: IntProperty(
        name="Expression Index",
        description="Specify an expression index to be overwritten.",
        default=-1,
        options={'SKIP_SAVE'}
    )
    side: EnumProperty(
        name="Expression Side",
        items=(
            ('L', "Left", "Expression affects only left side of the face. (Can create a mirror expression)"),
            ('N', "All", "Expression affects the whole face. (Left and right side bones are animated)"),
            ('R', "Right", "Expression affects only right side of the face. (Can create a mirror expression)"),
        ),
        options={'SKIP_SAVE'},
        default='N',
    )
    anim_mode: EnumProperty(
        name='Animation Mode',
        items=(
            ('ADD', "Add", "Add all animation in the specified expression"),
            ('REPLACE', "Replace", "Replace all animation in the specified expression")
        ),
        default='REPLACE',
        options={'SKIP_SAVE'},
    )
    is_new_rigify_rig: BoolProperty(
        name="New Rigify Rig",
        description="Use this option if you are using the new Rigify face rig.",
        default=False,
        options={'SKIP_SAVE'}
    )

    @ classmethod
    def poll(cls, context):
        if futils.get_faceit_armature():
            return True

    def execute(self, context):

        scene = context.scene
        state_dict = futils.save_scene_state(context)

        rig = futils.get_faceit_armature()
        if not rig:
            self.report({'ERROR'}, "Can't find the faceit rig. Cancelling procedural eyeblinks")
            return {'CANCELLED'}

        backup_action = bpy.data.actions.get("faceit_shape_action")
        action = bpy.data.actions.get("overwrite_shape_action")

        if not backup_action:
            backup_action = bpy.data.actions.new("faceit_shape_action")
        if not action:
            action = bpy.data.actions.new("overwrite_shape_action")

        # scene settings
        auto_key = scene.tool_settings.use_keyframe_insert_auto
        scene.tool_settings.use_keyframe_insert_auto = False

        # obj_save = None
        if context.object != rig:
            if futils.get_object_mode_from_context_mode(context.mode) != 'OBJECT' and context.object is not None:
                # obj_save = context.object
                bpy.ops.object.mode_set()
            futils.clear_object_selection()
            futils.set_active_object(rig.name)

        bpy.ops.object.mode_set(mode='POSE')

        if scene.is_nla_tweakmode:
            futils.exit_nla_tweak_mode(context)

        expression_item = scene.faceit_expression_list[self.expression_index]
        frame = expression_item.frame

        # print(
        #     f"procedural expression {expression_item.name}:\
        #     frame: {frame}, \
        #     side: {expression_item.side}\
        #     mirror: {expression_item.mirror_name},"
        # )

        # Remove keyframes and reset pose
        if self.anim_mode == 'REPLACE':
            a_utils.remove_all_animation_for_frame(action, frame)
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()

        scene.frame_set(frame)

        def get_bone_delta(bone1, bone2) -> Vector:
            '''returns object space vector between two pose bones'''
            pos1 = bone1.matrix.translation
            pos2 = bone2.matrix.translation
            vec = pos1 - pos2
            return vec

        def add_vector_to_bone_position(pose_bone, vec) -> None:
            '''Add a vector to the given bones location'''
            new_pos = pose_bone.matrix.translation - vec  # * 0.9
            pose_bone.matrix.translation = new_pos
            pose_bone.keyframe_insert(data_path='location', frame=frame)

        def get_copy_location_influence(pose_bone) -> float:
            '''Return the copy location constraints influence. Return 0.0 if no constraint.'''
            constraint_influence = 0.0
            copy_location_constraint = pose_bone.constraints.get("Copy Location")
            if copy_location_constraint:
                constraint_influence = copy_location_constraint.influence
            return constraint_influence

        # All bottom lid bones
        bot_inner_lid = rig.pose.bones.get(f"lid.B.{self.side}.001")
        bot_mid_lid = rig.pose.bones.get(f"lid.B.{self.side}.002")
        bot_outer_lid = rig.pose.bones.get(f"lid.B.{self.side}.003")
        # All upper lid bones
        top_outer_lid = rig.pose.bones.get(f"lid.T.{self.side}.001")
        top_mid_lid = rig.pose.bones.get(f"lid.T.{self.side}.002")
        top_inner_lid = rig.pose.bones.get(f"lid.T.{self.side}.003")
        # Calculate a delta vector for each pair (top to bottom)
        mid_delta = get_bone_delta(top_mid_lid, bot_mid_lid)
        if not self.is_new_rigify_rig:
            outer_lid_delta = get_bone_delta(top_outer_lid, bot_outer_lid)
            inner_lid_delta = get_bone_delta(top_inner_lid, bot_inner_lid)
            # Remove constraint influence from the outer and inner lid bones
            outer_lid_delta -= mid_delta * get_copy_location_influence(top_outer_lid)
            inner_lid_delta -= mid_delta * get_copy_location_influence(top_inner_lid)
        # Apply a constant offset to lower lid bones
        offset_multiplier = 0.9
        mid_delta *= offset_multiplier
        # Apply the vector to each top lid bone
        add_vector_to_bone_position(top_mid_lid, mid_delta)
        if not self.is_new_rigify_rig:
            outer_lid_delta *= offset_multiplier
            inner_lid_delta *= offset_multiplier
            add_vector_to_bone_position(top_outer_lid, outer_lid_delta)
            add_vector_to_bone_position(top_inner_lid, inner_lid_delta)

        a_utils.backup_expression(action, backup_action, frame=frame)
        scene.tool_settings.use_keyframe_insert_auto = auto_key
        # scene.frame_current = scene.frame_start
        futils.restore_scene_state(context, state_dict)
        return {'FINISHED'}


class FACEIT_OT_ProceduralMouthClose(bpy.types.Operator):
    # tooltip
    """
    Procedurally create the animations that need to be adapted to character style
    - mouth close is the delta animation between jaw open and lips closed
    - eye blink is the blinking animation that needs to adapted to eye shape
    """

    bl_idname = "faceit.procedural_mouth_close"
    bl_label = "Procedural MouthClose expression"
    bl_options = {'UNDO', 'INTERNAL'}

    jaw_open_expression: StringProperty(
        name="The jaw open expression name",
        default="jawOpen",
    )
    mouth_close_expression: StringProperty(
        name="The mouthClosed expression name",
        default="mouthClosed",
    )
    is_new_rigify_rig: BoolProperty(
        name="New Rigify Face Rig",
        default=False,
    )

    @ classmethod
    def poll(cls, context):
        if futils.get_faceit_armature():
            return True

    def execute(self, context):

        state_dict = futils.save_scene_state(context)
        scene = context.scene
        rig = futils.get_faceit_armature()
        backup_action = bpy.data.actions.get("faceit_shape_action")
        action = bpy.data.actions.get("overwrite_shape_action")

        if not backup_action:
            backup_action = bpy.data.actions.new("faceit_shape_action")
        if not action:
            action = bpy.data.actions.new("overwrite_shape_action")

        mode_save = futils.get_object_mode_from_context_mode(context.mode)
        if context.object != rig:
            if mode_save != 'OBJECT' and context.object is not None:
                bpy.ops.object.mode_set()
            futils.clear_object_selection()
            futils.set_active_object(rig.name)

        bpy.ops.object.mode_set(mode='POSE')

        # scene settings
        if scene.is_nla_tweakmode:
            futils.exit_nla_tweak_mode(context)

        expression_list = scene.faceit_expression_list

        jaw_open_shape = expression_list.get(self.jaw_open_expression)
        mouth_close_shape = expression_list.get(self.mouth_close_expression)

        jaw_open_shape_frame = jaw_open_shape.frame
        mouth_close_shape_frame = mouth_close_shape.frame

        if jaw_open_shape and mouth_close_shape:

            a_utils.ensure_mouth_lock_rig_drivers(rig)

            # for each pose bone: get the delta vector that should be applied to the mouth close shape
            lip_pose_bones = [
                "lip.T.L.001",
                "lip.T",
                "lip.T.R.001",
                "lip.B.L.001",
                "lip.B",
                "lip.B.R.001",
                "lips.L",
                "lips.R",
            ]
            if self.is_new_rigify_rig:
                lip_pose_bones.remove("lips.L")
                lip_pose_bones.remove("lips.R")
                lip_pose_bones.append("lip_end.L.001")
                lip_pose_bones.append("lip_end.R.001")

            a_utils.remove_all_animation_for_frame(action, mouth_close_shape.frame)

            scene.frame_set(mouth_close_shape_frame)
            bpy.ops.pose.select_all(action='SELECT')
            bpy.ops.pose.transforms_clear()
            bpy.ops.pose.select_all(action='DESELECT')

            for b_name in lip_pose_bones:
                rig.keyframe_insert(
                    data_path=f"pose.bones[\"{b_name}\"].location",
                    frame=mouth_close_shape_frame)

            a_utils.copy_keyframe(
                action, frame_from=jaw_open_shape_frame, frame_to=mouth_close_shape_frame,
                dp_filter=["pose.bones[\"jaw_master\"]"])

            frames_value_dict = {
                "original": [-10, 1],
                "new": [-9, 0],
            }

            jaw_pb = rig.pose.bones.get("jaw_master")
            for value, frames in frames_value_dict.items():
                if value == "new":
                    jaw_pb["mouth_lock"] = 1
                else:
                    jaw_pb["mouth_lock"] = 0

                for f in frames:
                    rig.keyframe_insert(
                        data_path="pose.bones[\"jaw_master\"][\"mouth_lock\"]",
                        frame=mouth_close_shape_frame + f)

        bpy.ops.object.mode_set(mode=mode_save)
        a_utils.backup_expression(action, backup_action, frame=mouth_close_shape_frame)

        scene.frame_current = scene.frame_start
        futils.restore_scene_state(context, state_dict)
        return {'FINISHED'}


def update_action_name(self, context):
    self.action_exists = self.action_name in bpy.data.actions


class NewActionBase():
    '''Creates a new Action.'''
    bl_label = "New Action"
    bl_options = {'REGISTER', 'UNDO'}

    action_name: bpy.props.StringProperty(
        name="Action Name",
        default="",
        options={'SKIP_SAVE'},
        update=update_action_name
    )
    use_fake_user: BoolProperty(
        name="Use Fake User",
        default=True,
        description="Save this action, even if it has no users."
    )
    overwrite_action: BoolProperty(
        name="Overwrite Existing",
        default=False,
        description="Overwrite existing action with the same name. Else, create a new action with nr appendix",
        options={'SKIP_SAVE'},
    )
    action_exists: BoolProperty(
        name="Action Exists",
        options={'HIDDEN', 'SKIP_SAVE'},
        default=False,
    )

    @ classmethod
    def poll(cls, context):
        return True

    def get_action_name(self):
        action_name = ""
        ctrl_rig = futils.get_faceit_control_armature()
        if not self.action_name:
            action_name = ctrl_rig.name + "Action"
        return action_name

    def invoke(self, context, event):
        if not self.action_name:
            self.action_name = self.get_action_name()
        if self.action_name in bpy.data.actions:
            self.action_exists = True
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "action_name")
        if self.action_exists:
            layout.prop(self, "overwrite_action")
            # layout.label(text="Action already exists", icon='ERROR')
        if self.use_fake_user:
            icon = 'FAKE_USER_ON'
        else:
            icon = 'FAKE_USER_OFF'
        layout.prop(self, "use_fake_user", icon=icon)

    def populate_action(self, context, action):
        # Assign the action to the target id(s) here.
        ctrl_rig = futils.get_faceit_control_armature()
        if not ctrl_rig.animation_data:
            ctrl_rig.animation_data_create()
        ctrl_rig.animation_data.action = action

    def execute(self, context):
        if not self.action_name:
            self.action_name = self.get_action_name()
        actions = bpy.data.actions
        if self.overwrite_action and self.action_exists:
            action = actions.get(self.action_name)
            if action:
                bpy.data.actions.remove(action)
        new_action = actions.new(name=self.action_name)
        if self.use_fake_user:
            new_action.use_fake_user = True
        self.populate_action(context, new_action)
        return {'FINISHED'}


class FACEIT_OT_NewAction(NewActionBase, bpy.types.Operator):
    '''Creates a new Action and OPTIONALLY activates it for all Objects registered in Faceit'''
    bl_idname = "faceit.new_action"
    bl_label = "New Shape Key Action"

    @ classmethod
    def poll(cls, context):
        return super().poll(context)

    def get_action_name(self):
        return "MocapAction"

    def populate_action(self, context, action):
        bpy.ops.faceit.populate_action(action_name=action.name)


class FACEIT_OT_NewHeadAction(NewActionBase, bpy.types.Operator):
    '''Creates a new Action and OPTIONALLY activates it for all Objects registered in Faceit'''
    bl_idname = "faceit.new_head_action"
    bl_label = "New Head Action"

    @ classmethod
    def poll(cls, context):
        return super().poll(context) and bpy.context.scene.faceit_head_target_object is not None

    def get_action_name(self):
        action_name = ""
        head_obj = bpy.context.scene.faceit_head_target_object
        if head_obj:
            action_name = head_obj.name + "Action"
        return action_name

    def populate_action(self, context, action):
        bpy.ops.faceit.populate_head_action(action_name=action.name)


class FACEIT_OT_NewCtrlRigAction(NewActionBase, bpy.types.Operator):
    '''Creates a new Ctrl Rig Action.'''
    bl_idname = "faceit.new_ctrl_rig_action"
    bl_label = "New Ctrl Rig Action"

    @ classmethod
    def poll(cls, context):
        return super().poll(context) and futils.get_faceit_control_armature()

    def get_action_name(self):
        action_name = ""
        ctrl_rig = futils.get_faceit_control_armature()
        if not self.action_name:
            action_name = ctrl_rig.name + "Action"
        return action_name

    def populate_action(self, context, action):
        # Assign the action to the target id(s) here.
        ctrl_rig = futils.get_faceit_control_armature()
        if not ctrl_rig.animation_data:
            ctrl_rig.animation_data_create()
        ctrl_rig.animation_data.action = action


class FACEIT_OT_PopulateAction(bpy.types.Operator):
    '''Populates the selected Action to all Objects registered with Faceit'''
    bl_idname = "faceit.populate_action"
    bl_label = "Activate Action"
    bl_options = {'UNDO', 'INTERNAL'}

    action_name: StringProperty(
        name="New Action",
        default="",
    )
    remove_action: BoolProperty(
        name="Remove Action",
        default=False,
        options={'SKIP_SAVE'}
    )
    set_mocap_action: BoolProperty(
        name="Set Mocap Action",
        default=True,
        description="Whether to set the active mocap action property",
        options={'SKIP_SAVE', 'HIDDEN'}
    )

    def execute(self, context):

        scene = context.scene
        faceit_objects = futils.get_faceit_objects_list()

        if self.remove_action:
            new_action = None
        else:
            if self.action_name:
                new_action = bpy.data.actions.get(self.action_name)
            else:
                new_action = scene.faceit_mocap_action

            if not new_action:
                self.report({'WARNING'}, "It seems the Action you want to pass does not exist")
                return {'CANCELLED'}

        for obj in faceit_objects:
            shape_keys = obj.data.shape_keys
            if not shape_keys:
                continue
            if not shape_keys.animation_data:
                shape_keys.animation_data_create()
            # Reset Animation values
            all_target_shapes = get_all_set_target_shapes(scene.faceit_arkit_retarget_shapes)
            all_target_shapes.extend(get_all_set_target_shapes(scene.faceit_a2f_retarget_shapes))
            sk_utils.set_rest_position_shape_keys(expressions_filter=all_target_shapes)

            shape_keys.animation_data.action = new_action

        if self.set_mocap_action:
            scene.faceit_mocap_action = new_action
            frame_range = futils.get_action_frame_range(new_action)
            if frame_range[1] - frame_range[0] > 1:
                scene.frame_start = scene.frame_current = int(frame_range[0])
                scene.frame_end = int(frame_range[1])

        return {'FINISHED'}


class FACEIT_OT_PopulateHeadAction(bpy.types.Operator):
    '''Populates the selected Action to the registered head object'''
    bl_idname = "faceit.populate_head_action"
    bl_label = "Activate Head Action"
    bl_options = {'UNDO', 'INTERNAL'}

    action_name: StringProperty(
        name="New Action",
        default="",
    )
    remove_action: BoolProperty(
        name="Remove Action",
        default=False,
        options={'SKIP_SAVE'}
    )
    set_mocap_action: BoolProperty(
        name="Set Mocap Action",
        default=True,
        description="Whether to set the active mocap action property",
        options={'SKIP_SAVE', 'HIDDEN'}
    )

    def execute(self, context):

        scene = context.scene
        head_obj = scene.faceit_head_target_object

        if self.remove_action:
            new_action = None
            head_obj.animation_data.action = new_action
        else:
            if self.action_name:
                new_action = bpy.data.actions.get(self.action_name)
            else:
                new_action = scene.faceit_head_action

            if not new_action:
                self.report({'WARNING'}, "It seems the Action you want to pass does not exist")
                return {'CANCELLED'}

        if not head_obj.animation_data:
            head_obj.animation_data_create()
        # Reset Animation values
        bpy.ops.faceit.reset_head_pose('EXEC_DEFAULT')

        if self.set_mocap_action:
            scene.faceit_head_action = new_action
            frame_range = futils.get_action_frame_range(new_action)
            if frame_range[1] - frame_range[0] > 1:
                scene.frame_start = scene.frame_current = int(frame_range[0])
                scene.frame_end = int(frame_range[1])

        return {'FINISHED'}


class FACEIT_OT_SetBodyBindPose(bpy.types.Operator):
    '''Sets the current pose as the bind pose for the body'''
    bl_idname = "faceit.set_body_bind_pose"
    bl_label = "Reset Pose"
    bl_options = {'UNDO', 'INTERNAL'}
    rig_name: StringProperty(
        name="Rig Name",
        default="",
        options={'SKIP_SAVE'}
    )
    check_warnings: BoolProperty(
        name="Check Warnings",
        default=False,
        options={'SKIP_SAVE'}
    )

    @ classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        rig = scene.objects.get(self.rig_name)
        if rig:
            if rig.animation_data:
                if rig.animation_data.action:
                    rig.animation_data.action = None
            for pb in rig.pose.bones:
                reset_pb(pb)
        else:
            self.report({'WARNING'}, f"No Rig found with the name {self.rig_name}")
        if self.check_warnings:
            bpy.ops.faceit.face_object_warning_check('EXEC_DEFAULT', item_name='ALL')
        return {'FINISHED'}
