import bpy
import webbrowser
from ..core import faceit_utils as futils
from ..core import vgroup_utils as vg_utils


class FACEIT_OT_AddFacialPart(bpy.types.Operator):
    '''Register the selected Object for Faceit Process'''
    bl_idname = 'faceit.add_facial_part'
    bl_label = 'Register Selected Object'
    bl_options = {'UNDO', 'INTERNAL'}

    facial_part: bpy.props.StringProperty(
        name='Part',
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        if obj is not None:
            return (obj.type == 'MESH') and \
                (obj.name not in context.scene.faceit_face_objects or len(context.selected_objects) > 1)

    def execute(self, context):
        scene = context.scene
        face_objects = scene.faceit_face_objects

        # hidden object is not in selected objects, append context
        objects_add = list(filter(lambda x: x.type == 'MESH', context.selected_objects))

        if not objects_add:
            objects_add.append(context.object)

        for obj in objects_add:
            # check if that item exists
            obj_exists = any([obj.name == item.name for item in face_objects])
            if not obj_exists:
                item = face_objects.add()
                item.name = obj.name
                item.obj_pointer = obj
                # check for warnings
                bpy.ops.faceit.face_object_warning_check('INVOKE_DEFAULT', item_name=item.name, set_show_warnings=False)

            # set active index to new item
            scene.faceit_face_index = face_objects.find(obj.name)

        return {'FINISHED'}


class FACEIT_OT_RemoveFacialPart(bpy.types.Operator):
    '''Remove the selected Character Geometry from Registration.'''
    bl_idname = 'faceit.remove_facial_part'
    bl_label = 'Remove Facial Parts'
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
        obj = context.object
        if obj is not None:
            return True  # obj.name in context.scene.faceit_face_objects

    def invoke(self, context, event):
        scene = context.scene
        if self.prompt:
            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def execute(self, context):

        scene = context.scene
        face_objects = scene.faceit_face_objects
        face_index = scene.faceit_face_index

        def _remove_faceit_item(item):
            if self.clear_vertex_groups:
                obj = futils.get_object(item.name)
                try:
                    remove_groups = vg_utils.remove_faceit_vertex_grps(obj)
                    self.report({'INFO'}, 'Cleared Faceit Vertex Groups {} on {}.'.format(remove_groups, obj.name))
                except AttributeError:

                    self.report({'INFO'}, 'No Vertex Groups found on Object.')
                    pass
            item_index = face_objects.find(item.name)
            if item_index == face_index:
                scene.faceit_face_index -= 1
            face_objects.remove(item_index)

        # remove from face objects
        if len(face_objects) > 0:
            if self.remove_item:
                item = face_objects[self.remove_item]
            else:
                item = face_objects[scene.faceit_face_index]

            _remove_faceit_item(item)

        scene.faceit_workspace.active_tab = 'SETUP'

        return {'FINISHED'}


class FACEIT_OT_ClearFaceitObjects(bpy.types.Operator):
    '''Remove the selected Character Geometry from Registration.'''
    bl_idname = 'faceit.clear_faceit_objects'
    bl_label = 'Clear Facial Parts'
    bl_options = {'UNDO', 'INTERNAL'}

    clear_vertex_groups: bpy.props.BoolProperty(
        name='Clear Vertex Groups',
        description='Clear the assigned vertex groups or keep them on the object',
        default=False,
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        return context.scene.faceit_face_objects

    def execute(self, context):

        scene = context.scene
        face_objects_list = scene.faceit_face_objects

        if self.clear_vertex_groups:
            for obj in futils.get_faceit_objects_list():
                try:
                    remove_groups = vg_utils.remove_faceit_vertex_grps(obj)
                    self.report({'INFO'}, 'Cleared Faceit Vertex Groups {} on {}.'.format(remove_groups, obj.name))
                except AttributeError:

                    self.report({'INFO'}, 'No Vertex Groups found on Object.')
                    pass

        scene.faceit_face_index = 0
        face_objects_list.clear()
        scene.faceit_workspace.active_tab = 'SETUP'

        return {'FINISHED'}


class FACEIT_OT_MoveFaceObject(bpy.types.Operator):
    '''Move the Face Object to new index'''
    bl_idname = 'faceit.move_face_object'
    bl_label = 'Move'
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
        return context.scene.faceit_face_objects

    def move_index(self, context, flist, index):
        list_length = len(flist) - 1
        new_index = index + (-1 if self.direction == 'UP' else 1)
        context.scene.faceit_face_index = max(0, min(new_index, list_length))

    def execute(self, context):
        scene = context.scene
        index = scene.faceit_face_index
        faceit_objects = scene.faceit_face_objects

        new_index = index + (-1 if self.direction == 'UP' else 1)
        faceit_objects.move(new_index, index)
        self.move_index(context, faceit_objects, index)

        return{'FINISHED'}


class FACEIT_OT_GoToTab(bpy.types.Operator):
    '''You have to generate the rig first...'''
    bl_idname = 'faceit.go_to_tab'
    bl_label = 'Generate Rig first!'
    bl_options = {'INTERNAL'}

    tab: bpy.props.StringProperty(
        name='Tab',
        default='CREATE'
    )

    def execute(self, context):
        context.scene.faceit_workspace.active_tab = self.tab
        return {'FINISHED'}


class FACEIT_OT_OpenWeb(bpy.types.Operator):
    '''Opens a Weblink in the Browser. Can be disabled in the Add-on Preferences'''
    bl_idname = 'faceit.open_web'
    bl_label = 'Web Link'

    link: bpy.props.StringProperty(
        name='Link to webpage',
        default='https://faceit-doc.readthedocs.io/en/latest'
    )

    def execute(self, context):

        webbrowser.open(self.link)
        return {'FINISHED'}
