
import bpy
from bpy.props import EnumProperty

from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils
from ..core.retarget_list_base import (EditTargetShapeBase, RemoveTargetShapeBase,
                                       ResetRegionsOperatorBase,
                                       SetDefaultRegionsBase)
from . import control_rig_utils as ctrl_utils


class FACEIT_OT_ResetCtrlRigRegions(ResetRegionsOperatorBase, bpy.types.Operator):
    bl_idname = 'faceit.reset_ctrl_rig_regions'
    is_ctrl_rig_regions = True

    @classmethod
    def poll(cls, context):
        if super().poll(context):
            if hasattr(context.scene, 'faceit_control_armature'):
                return hasattr(context.scene.faceit_control_armature, 'faceit_ctrl_face_regions')


class FACEIT_OT_SetDefaultCrigRegions(SetDefaultRegionsBase, bpy.types.Operator):
    ''' Try to set the correct regions for the source/target shapes'''
    bl_idname = 'faceit.set_default_crig_regions'

    @classmethod
    def poll(cls, context):
        return super().poll(context)

    @staticmethod
    def get_face_regions(context):
        ctrl_rig = context.scene.faceit_control_armature
        if ctrl_rig:
            return ctrl_rig.faceit_crig_face_regions


class FACEIT_OT_RemoveCrigTargetObject(bpy.types.Operator):
    ''' Remove object from target objects of active control rig. '''
    bl_idname = 'faceit.remove_crig_target_object'
    bl_label = 'Remove Target Object'
    bl_options = {'UNDO', 'INTERNAL'}

    prompt: bpy.props.BoolProperty()

    clear_vertex_groups: bpy.props.BoolProperty(
        name='Clear Registered Parts',
        description='Clear the assigned vertex groups or keep them on the object',
        default=False,
        options={'SKIP_SAVE'},
    )
    remove_item: bpy.props.StringProperty(
        default='',
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    @classmethod
    def poll(cls, context):
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if ctrl_rig.library or ctrl_rig.override_library:
                return False
            if ctrl_rig.faceit_crig_objects:
                return True

    def execute(self, context):

        scene = context.scene
        c_rig = futils.get_faceit_control_armature()

        c_rig_objects = c_rig.faceit_crig_objects
        list_index = c_rig.faceit_crig_objects_index

        def _remove_item(item):
            item_index = c_rig_objects.find(item.name)
            if item_index == list_index:
                scene.faceit_face_index -= 1
            c_rig_objects.remove(item_index)

        # remove from face objects
        if len(c_rig_objects) > 0:
            if self.remove_item:
                item = c_rig_objects[self.remove_item]
            else:
                item = c_rig_objects[scene.faceit_face_index]

            _remove_item(item)

        return {'FINISHED'}


class FACEIT_OT_AddCrigTargetObject(bpy.types.Operator):
    ''' Register the selected Object as target for the active control rig '''
    bl_idname = 'faceit.add_crig_target_object'
    bl_label = 'Add Control Rig Target Object'
    bl_options = {'UNDO', 'INTERNAL'}

    facial_part: bpy.props.StringProperty(
        name='Part',
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        ctrl_rig = futils.get_faceit_control_armature()
        if obj and ctrl_rig:
            if ctrl_rig.library or ctrl_rig.override_library:
                return False
            return (obj.type == 'MESH') and (obj.name not in ctrl_rig.faceit_crig_objects or len(context.selected_objects) > 1)

    def execute(self, context):
        ctrl_rig = futils.get_faceit_control_armature()
        crig_objects = ctrl_rig.faceit_crig_objects

        # hidden object is not in selected objects, append context
        objects_add = list(filter(lambda x: x.type == 'MESH', context.selected_objects))

        if not objects_add:
            objects_add.append(context.object)

        for obj in objects_add:
            # check if that item exists
            obj_exists = any([obj.name == item.name for item in crig_objects])
            if not obj_exists:
                item = crig_objects.add()
                item.name = obj.name
                item.obj_pointer = obj

            # set active index to new item
        ctrl_rig.faceit_crig_objects_index = crig_objects.find(obj.name)

        return {'FINISHED'}


def get_shape_keys_from_crig_target_objects_enum(self, context):
    '''Returns a items list to be used in EnumProperties'''
    # blender is prone to crash without making shapes global
    global shapes
    shapes = []

    ctrl_rig = futils.get_faceit_control_armature()

    if context is None:
        print('get_shape_keys_from_main_object --> Context is None')
        return shapes
    # faceit_objects = futils.get_faceit_objects_list()
    crig_objects = ctrl_utils.get_crig_objects_list(ctrl_rig)

    if crig_objects:
        shape_key_names = sk_utils.get_shape_key_names_from_objects(crig_objects)

        for i, name in enumerate(shape_key_names):

            shapes.append((name, name, name, i))
    else:
        print('no shapes found --> add None')
        shapes.append(("None", "None", "None"))

    return shapes


class FACEIT_OT_EditCrigTargetShape(EditTargetShapeBase, bpy.types.Operator):
    bl_idname = 'faceit.edit_crig_target_shape'
    bl_property = 'new_target_shape'

    new_target_shape: EnumProperty(
        items=get_shape_keys_from_crig_target_objects_enum, name='Change target Shape',
        description='Choose a Shape Key as target for retargeting this shape. \nThe shapes listed are from the Main Object registered in Setup panel.\n'
    )

    @staticmethod
    def get_retarget_shapes():
        ''' Get the retarget_list property group '''
        ctrl_rig = bpy.context.scene.faceit_control_armature
        if ctrl_rig:
            return ctrl_rig.faceit_crig_targets

    @classmethod
    def poll(cls, context):
        ctrl_rig = context.scene.faceit_control_armature
        if super().poll(context):
            if ctrl_rig.library or ctrl_rig.override_library:
                return False
            if ctrl_rig.faceit_crig_objects:
                return True


class FACEIT_OT_RemoveCrigTargetShape(RemoveTargetShapeBase, bpy.types.Operator):
    bl_idname = 'faceit.remove_crig_target_shape'

    @staticmethod
    def get_retarget_shapes():
        ''' Get the retarget_list property group '''
        ctrl_rig = bpy.context.scene.faceit_control_armature
        if ctrl_rig:
            return ctrl_rig.faceit_crig_targets

    @classmethod
    def poll(cls, context):
        ctrl_rig = context.scene.faceit_control_armature
        if super().poll(context):
            if ctrl_rig.library or ctrl_rig.override_library:
                return False
            return True
