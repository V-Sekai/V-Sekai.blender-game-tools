import bpy
from bpy.app.handlers import persistent


@persistent
def faceit_scene_update_handler(scene):
    obj = scene.faceit_control_armature
    if obj is not None:
        if obj.name not in scene.objects:
            scene.faceit_control_armature = None
    face_objects = scene.faceit_face_objects
    if face_objects:
        for obj in face_objects:
            if obj.name not in scene.objects:
                index = scene.faceit_face_objects.find(obj.name)
                scene.faceit_face_objects.remove(index)

        if scene.faceit_workspace.active_tab == 'SETUP':
            context = bpy.context
            active_obj = context.active_object
            if not obj:
                return
            index = face_objects.find(active_obj.name)
            if index != -1:
                if scene.faceit_active_object != context.active_object.name:
                    scene.faceit_active_object = context.active_object.name
                    scene.faceit_face_index = index
                    # Reset faceit_face_index_updated to a value out of range
                    scene.faceit_face_index_updated = -2


def register():
    if faceit_scene_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(faceit_scene_update_handler)


def unregister():
    if faceit_scene_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(faceit_scene_update_handler)
