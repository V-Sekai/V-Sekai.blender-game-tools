import bpy


from ..core import faceit_data as fdata
from ..core import faceit_utils as futils
from ..core import shape_key_utils as sk_utils


class FACEIT_OT_ChangeNameScheme(bpy.types.Operator):
    '''Change the retargeting list name scheme'''
    bl_idname = 'faceit.change_retargeting_name_scheme'
    bl_label = 'Change Naming Scheme'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        scene = context.scene
        retarget_list = scene.faceit_arkit_retarget_shapes

        name_scheme = scene.faceit_retargeting_naming_scheme

        if name_scheme == 'ARKIT':
            shape_dict = fdata.get_arkit_shape_data()
        elif name_scheme == 'FACECAP':
            shape_dict = fdata.get_face_cap_shape_data()

        new_index_dict = {}
        for arkit_name, data in shape_dict.items():

            new_index = data['index']
            display_name = data['name']

            found_item = retarget_list[arkit_name]

            new_index_dict[arkit_name] = new_index
            found_item.display_name = display_name

        def find_new_index(index):
            arkit_name = retarget_list[index].name
            return new_index_dict[arkit_name]

        # Sort by new indices (bubble sort)
        for passesLeft in range(len(retarget_list) - 1, 0, -1):
            for index in range(passesLeft):
                idx_1, idx_2 = find_new_index(index), find_new_index(index + 1)
                if idx_1 > idx_2:
                    retarget_list.move(index, index + 1)

        return{'FINISHED'}


class FACEIT_OT_RetargetNames(bpy.types.Operator):
    '''Apply the ARKit names to the specified Shape Keys'''
    bl_idname = 'faceit.retarget_names'
    bl_label = 'Apply Source Naming'
    bl_description = 'Applies the names from the source shapes to the target shape keys on all registered objects.'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        # return context.mode != 'POSE'
        return True
        # if context.mode == 'OBJECT':
        #     return context.scene.faceit_arkit_retarget_shapes

    def execute(self, context):

        scene = context.scene
        faceit_objects = futils.get_faceit_objects_list()
        retarget_list = scene.faceit_arkit_retarget_shapes

        for obj in faceit_objects:

            if not sk_utils.has_shape_keys(obj):
                continue
            shape_keys = obj.data.shape_keys.key_blocks

            for item in retarget_list:

                target_shapes = item.target_shapes

                if not target_shapes:
                    continue

                target_shape_item = None

                try:
                    target_shape_item = target_shapes[item.target_list_index]
                except IndexError:
                    target_shape_item = target_shapes[0]

                if not target_shape_item:
                    continue

                display_name = item.display_name

                sk = shape_keys.get(target_shape_item.name)
                if sk:
                    sk.name = display_name
                else:
                    self.report({'WARNING'}, 'Did not find shape {}'.format(target_shape_item.name))

                if obj == faceit_objects[-1]:
                    target_shape_item.name = display_name

        return{'FINISHED'}
