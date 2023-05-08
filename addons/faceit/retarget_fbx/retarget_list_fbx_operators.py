
import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty

from ..core import shape_key_utils as sk_utils
from ..core.detection_manager import detect_shape
from ..core.faceit_utils import (get_faceit_control_armature,
                                 get_faceit_objects_list)
from ..core.retarget_list_base import (ClearTargetShapeBase, EditTargetShapeBase,
                                       RemoveTargetShapeBase, RetargetingBase)
from ..ctrl_rig.control_rig_utils import get_crig_objects_list


class FBXRetargetBase(RetargetingBase):

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    @staticmethod
    def get_retarget_shapes():
        ''' Get the retarget_list property group '''
        return bpy.context.scene.faceit_retarget_fbx_mapping.mapping_list


class FACEIT_OT_EditFBXTargetShape(EditTargetShapeBase, FBXRetargetBase, bpy.types.Operator):
    bl_idname = 'faceit.edit_fbx_target_shape'
    bl_property = 'new_target_shape'


class FACEIT_OT_RemoveFBXTargetShape(RemoveTargetShapeBase, FBXRetargetBase, bpy.types.Operator):
    bl_idname = 'faceit.remove_fbx_target_shape'


class FACEIT_OT_ClearFBXTargetShapes(ClearTargetShapeBase, FBXRetargetBase, bpy.types.Operator):
    bl_idname = 'faceit.clear_fbx_target_shapes'


class FACEIT_OT_InitFBXRetargeting(bpy.types.Operator):
    '''Initialize the retargeting list and try to match shapes automatically'''
    bl_idname = 'faceit.init_fbx_retargeting'
    bl_label = 'Initialize Retargeting'
    bl_options = {'UNDO', 'INTERNAL'}

    levenshtein_ratio: FloatProperty(
        name='Similarity Ratio',
        default=1.0,
        description='The ratio can be used for fuzzy name comparison. Default: 1.0'
    )

    empty: BoolProperty(
        name='Empty',
        default=False,
        description='Register with Empty Targets',
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    remove_prefix_source: StringProperty(
        name='Remove Prefix (Source)',
        description='Specify a Prefix that will be ignore during matching.'
    )
    remove_suffix_source: StringProperty(
        name='Remove Suffix (Source)',
        description='Specify a Suffix that will be ignore during matching.'
    )
    remove_prefix_target: StringProperty(
        name='Remove Prefix (Target)',
        description='Specify a Prefix that will be ignore during matching.'
    )
    remove_suffix_target: StringProperty(
        name='Remove Suffix (Target)',
        description='Specify a Suffix that will be ignore during matching.'
    )

    @classmethod
    def poll(cls, context):

        retarget_fbx_props = context.scene.faceit_retarget_fbx_mapping

        mapping_source = retarget_fbx_props.mapping_source

        if mapping_source == 'OBJECT':
            source = retarget_fbx_props.source_obj
        else:
            source = retarget_fbx_props.source_action

        target = retarget_fbx_props.target_obj is not None or retarget_fbx_props.mapping_target != 'TARGET'

        return source and target

    def invoke(self, context, event):
        if self.empty is False:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def execute(self, context):

        scene = context.scene

        retarget_fbx_props = scene.faceit_retarget_fbx_mapping
        retarget_list = retarget_fbx_props.mapping_list

        # | ------------------- MAPPING SOURCE ------------------------
        # | - Either a specific Object or a Shape Key Action (Shape Key Names)
        # | -----------------------------------------------------------
        mapping_source = retarget_fbx_props.mapping_source

        shape_key_names_source = []

        if self.empty:
            retarget_list.clear()
            return{'FINISHED'}

        if mapping_source == 'OBJECT':
            source_obj = retarget_fbx_props.source_obj
            if not source_obj:
                self.report({'ERROR'}, 'The Source Object is not valid')
                return{'CANCELLED'}

            if not sk_utils.has_shape_keys(source_obj):
                self.report({'ERROR'}, 'The Source Object has no Shape Keys')
                return{'CANCELLED'}

            shape_key_names_source = sk_utils.get_shape_key_names_from_objects([source_obj])

        elif mapping_source == 'ACTION':
            source_action = retarget_fbx_props.source_action
            if not source_action:
                self.report(
                    {'ERROR'},
                    'No registered objects found. Register Objects in Setup Panel or use single target object')
                return{'CANCELLED'}

            shape_key_names_source = sk_utils.get_shape_key_names_from_action(source_action)

        if not shape_key_names_source:
            self.report({'ERROR'}, 'No Shape Keys found in Source.')
            return{'CANCELLED'}

        # | ------------------- MAPPING TARGET ------------------------
        # | - Either a specific Object or all registered Objects (Shape Key Names)
        # | -----------------------------------------------------------
        mapping_target = retarget_fbx_props.mapping_target

        target_objects = []
        shape_key_names_target = []

        if mapping_target == 'TARGET':
            target_obj = retarget_fbx_props.target_obj
            if not target_obj:
                self.report({'ERROR'}, 'The Target Object is not valid')
                return{'CANCELLED'}
            if not sk_utils.has_shape_keys(target_obj):
                self.report({'ERROR'}, 'The Target Object has no Shape Keys')
                return{'CANCELLED'}

            target_objects = [target_obj, ]
            # shape_key_names_target = sk_utils.get_shape_key_names_from_objects([target_obj])

        elif mapping_target == 'FACEIT':
            target_objects = get_faceit_objects_list()
            if not target_objects:
                self.report(
                    {'ERROR'},
                    'No registered objects found. Register Objects in Setup Panel or use single target object')
                return{'CANCELLED'}

        elif mapping_target == 'CRIG':
            c_rig = get_faceit_control_armature()
            if c_rig:
                target_objects = get_crig_objects_list(c_rig)
            if not target_objects:
                self.report(
                    {'ERROR'},
                    'No registered objects found. Register Objects in Setup Panel or use single target object')
                return{'CANCELLED'}

        shape_key_names_target = sk_utils.get_shape_key_names_from_objects(target_objects)

        if not shape_key_names_target:
            self.report({'ERROR'}, 'the registered objects have no shape keys.')
            return{'CANCELLED'}

        match_names = {}
        new_names = []
        if self.remove_prefix_target or self.remove_suffix_target:
            new_names = []
            for name in shape_key_names_target:
                name_match = name
                if self.remove_prefix_target:
                    if name.startswith(self.remove_prefix_target):
                        name_match = name[len(self.remove_prefix_target):]
                if self.remove_suffix_target:
                    if name.endswith(self.remove_suffix_target):
                        name_match = name[:-len(self.remove_suffix_target)]
                new_names.append(name_match)
                match_names[name_match] = name

        retarget_list.clear()
        missing_shapes = []

        for _, source_shape in enumerate(shape_key_names_source):

            item = retarget_list.add()

            item.name = source_shape

            if self.empty:
                continue

            if self.remove_prefix_source:
                if source_shape.startswith(self.remove_prefix_source):
                    source_shape = source_shape[len(self.remove_prefix_source):]
            if self.remove_suffix_source:
                if source_shape.endswith(self.remove_suffix_source):
                    source_shape = source_shape[:-len(self.remove_suffix_source)]
            if new_names:
                found_shape = detect_shape(
                    new_names,
                    source_shape,
                    min_levenshtein_ratio=self.levenshtein_ratio,
                    remove_suffix=self.remove_suffix_target,
                )
                found_shape = match_names.get(found_shape)
            else:
                found_shape = detect_shape(
                    shape_key_names_target,
                    source_shape,
                    min_levenshtein_ratio=self.levenshtein_ratio,
                    remove_prefix=self.remove_prefix_target,
                    remove_suffix=self.remove_suffix_target,
                )
            if found_shape:

                target_item = item.target_shapes.add()
                target_item.name = found_shape
                shape_key_names_target.remove(found_shape)
                continue

            missing_shapes.append(source_shape)

        if missing_shapes:
            self.report(
                {'WARNING'}, 'Couldn\'t find all target shapes. Are the shape keys missing?')

        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}
