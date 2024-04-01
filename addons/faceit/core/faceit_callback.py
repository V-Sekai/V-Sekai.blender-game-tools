import bpy
import bmesh

from ..landmarks.landmarks_utils import unlock_3d_view


class FACEIT_OT_SubscribeSettings(bpy.types.Operator):
    '''Subscribe msgbus to the active object'''
    bl_idname = "faceit.subscribe_settings"
    bl_label = "Subscribe"

    def execute(self, context):
        context.scene.faceit_subscribed = False
        msgbus(self, context)
        return {'FINISHED'}


def msgbus(self, context):
    '''Activates the subscribtion to the active object'''
    if context.scene.faceit_subscribed is True:
        return

    subscribe_to_active_object = bpy.types.LayerObjects, "active"
    bpy.msgbus.subscribe_rna(
        key=subscribe_to_active_object,
        owner=self,
        args=(context,),
        notify=faceit_active_object_callback,
    )
    subscribe_to_mode = bpy.types.Object, "mode"
    bpy.msgbus.subscribe_rna(
        key=subscribe_to_mode,
        owner=self,
        args=(context,),
        notify=faceit_switch_modes_callback,
    )
    context.scene.faceit_subscribed = True


def faceit_switch_modes_callback(context):
    '''Runs when the object mode changes'''
    obj = context.object
    if obj is None:
        return
    if obj.name == "facial_landmarks":
        if obj.mode == 'EDIT':
            if obj["state"] == 3 and context.preferences.addons['faceit'].preferences.auto_lock_3d_view:
                bpy.ops.faceit.lock_3d_view_front('INVOKE_DEFAULT', set_edit_mode=False,
                                                  find_area_by_mouse_position=True)
        else:
            unlock_3d_view()


def faceit_active_object_callback(context):
    '''Runs every time the active object changes'''
    scene = context.scene
    active_object = bpy.context.active_object
    if active_object is None:
        return
    if active_object.name == "facial_landmarks":
        if bpy.context.preferences.addons["faceit"].preferences.use_vertex_size_scaling:
            bpy.context.preferences.themes[0].view_3d.vertex_size = bpy.context.preferences.addons["faceit"].preferences.landmarks_vertex_size
    else:
        if bpy.context.preferences.addons["faceit"].preferences.use_vertex_size_scaling:
            bpy.context.preferences.themes[0].view_3d.vertex_size = bpy.context.preferences.addons["faceit"].preferences.default_vertex_size
    # set the active control rig
    if active_object.get("ctrl_rig_version"):
        scene.faceit_control_armature = active_object
    # Set the active faceit_objects index
    if scene.faceit_workspace.active_tab in ('SETUP', 'BAKE'):
        if active_object.name in scene.faceit_face_objects:
            index = scene.faceit_face_objects.find(active_object.name)
            if index not in (-1, scene.faceit_face_index):
                scene.faceit_face_index = index
