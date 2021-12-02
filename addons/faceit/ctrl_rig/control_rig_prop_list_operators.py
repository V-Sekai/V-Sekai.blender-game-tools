
import bpy
from ..core import faceit_utils as futils
from bpy.props import EnumProperty, IntProperty, StringProperty

from ..core import shape_key_utils as sk_utils
from ..retargeting import retarget_list_utils as rutils
from . import control_rig_utils as ctrl_utils


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
    def poll(self, context):
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
    def poll(self, context):
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


class FACEIT_OT_EditCrigTargetShape(bpy.types.Operator):
    '''Edit target shape, add new or change selected'''
    bl_label = "Add Crig Target Shape"
    bl_idname = 'faceit.edit_crig_target_shape'
    bl_property = 'all_shapes'
    bl_options = {'UNDO'}

    operation: EnumProperty(
        name='Operation to perform',
        items=(
            ('ADD', 'ADD', 'ADD'),
            ('CHANGE', 'CHANGE', 'CHANGE'),
        ),
        default='ADD',
        options={'SKIP_SAVE', },

    )

    # Has to be named type for invoke_search_popup to work... wtf
    all_shapes: EnumProperty(
        items=get_shape_keys_from_crig_target_objects_enum, name='Change target Shape',
        description='Choose a Shape Key as target for retargeting this shape. \nThe shapes listed are from the Main Object registered in Setup panel.\n'
    )

    source_shape_index: IntProperty(
        name='Name of the Shape Item',
        default=-1,
    )

    target_shape: StringProperty(
        name='Name of the target shape',
        default='',
    )

    @classmethod
    def poll(cls, context):
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if ctrl_rig.library or ctrl_rig.override_library:
                return False
            if ctrl_rig.faceit_crig_targets:
                return True
        # return context.scene.faceit_retarget_shapes

    def invoke(self, context, event):
        wm = context.window_manager
        wm.invoke_search_popup(self)
        return {'FINISHED'}

    def execute(self, context):

        ctrl_rig = futils.get_faceit_control_armature()
        # check if target shapes have been assigend to other shape items....
        crig_targets = ctrl_rig.faceit_crig_targets
        list_item = crig_targets[self.source_shape_index]
        target_shapes = list_item.target_shapes
        target_shape_index = target_shapes.find(self.target_shape)

        if list_item:

            # Check if the target shape (type) is already assigned
            if rutils.is_target_shape_double(self.all_shapes, crig_targets):
                # pass
                source_shape = ''
                for _list_item in crig_targets:

                    if self.all_shapes in _list_item.target_shapes:

                        source_shape = _list_item.name

                self.report(
                    {'WARNING'},
                    'WARNING! The shape {} is already assigned to Source Shape {}'.format(
                        self.all_shapes, source_shape))
                # return {'CANCELLED'}

            if self.operation == 'CHANGE':
                if target_shapes and target_shape_index != -1:
                    item = target_shapes[target_shape_index]
                    if item:
                        item.name = self.all_shapes
            else:
                target_shape_count = len(list_item.target_shapes)
                item = target_shapes.add()
                item.name = self.all_shapes
                item.index = target_shape_count
                item.parent_idx = crig_targets.find(list_item.name)  # list_item.index

        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}


class FACEIT_OT_RemoveCrigTargetShape(bpy.types.Operator):
    bl_label = 'Remove Target Shape'
    bl_idname = 'faceit.remove_crig_target_shape'

    source_shape_index: IntProperty(
        name='Index of the Shape Item',
        default=0,
    )

    target_shape: StringProperty(
        name='Index of the Target Shape',
        default='',
    )

    @classmethod
    def poll(cls, context):
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if ctrl_rig.library or ctrl_rig.override_library:
                return False
            if ctrl_rig.faceit_crig_targets:
                return True
        # return context.scene.faceit_retarget_shapes

    def execute(self, context):

        ctrl_rig = futils.get_faceit_control_armature()
        # check if target shapes have been assigend to other shape items....
        crig_targets = ctrl_rig.faceit_crig_targets
        source_item = crig_targets[self.source_shape_index]
        target_shapes = source_item.target_shapes
        target_shape_index = target_shapes.find(self.target_shape)
        # retarget_list = scene.faceit_retarget_shapes

        # shape_item = retarget_list[self.parent_index]

        if target_shape_index != -1:
            # target_shape_index = source_item.target_shapes.find(self.target_shape)
            source_item.target_shapes.remove(target_shape_index)

        for region in context.area.regions:
            region.tag_redraw()

        return{'FINISHED'}
