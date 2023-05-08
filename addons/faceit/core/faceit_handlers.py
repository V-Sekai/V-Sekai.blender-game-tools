import bpy
from bpy.app.handlers import persistent

from ..core.faceit_utils import get_faceit_objects_list
from ..core.faceit_data import FACEIT_VERTEX_GROUPS
from ..core.modifier_utils import populate_bake_modifier_items
from ..landmarks.landmarks_utils import set_front_view, unlock_3d_view

landmarks_state_pre = 0
landmarks_active_pre = False


@persistent
def faceit_scene_update_handler(scene):
    active_object = bpy.context.object
    ctrl_rig = scene.faceit_control_armature
    if ctrl_rig is not None:
        if ctrl_rig.name not in scene.objects:
            scene.faceit_control_armature = None
            bpy.ops.faceit.clear_old_ctrl_rig_data()
    body_rig = scene.faceit_body_armature
    if body_rig is not None:
        if body_rig.name not in scene.objects:
            scene.faceit_body_armature = None
    rig = scene.faceit_armature
    if rig is not None:
        if rig.name not in scene.objects:
            bpy.data.objects.remove(rig, do_unlink=True)
            scene.faceit_armature = None
            if scene.faceit_expression_list:
                scene.faceit_armature_missing = True
                scene.faceit_shapes_generated = False
    faceit_objects = scene.faceit_face_objects
    if faceit_objects:
        if scene.faceit_workspace.active_tab in ('SETUP', 'BAKE'):
            if getattr(bpy.context.active_operator, "bl_idname", "") == "OBJECT_OT_delete":
                for obj_item in faceit_objects:
                    if obj_item.name not in scene.objects:
                        index = scene.faceit_face_objects.find(obj_item.name)
                        scene.faceit_face_objects.remove(index)
        if not scene.faceit_shapes_generated:
            if scene.faceit_workspace.active_tab in ('BAKE'):
                if active_object is not None:
                    populate_bake_modifier_items(objects=[active_object])
    if scene.faceit_shapes_generated:
        head_obj = scene.faceit_head_target_object
        if head_obj:  # and not scene.faceit_head_action:
            if head_obj.animation_data:
                action = head_obj.animation_data.action
                if action is not None and action != scene.faceit_head_action:
                    scene.faceit_head_action = action


@persistent
def faceit_undo_post_handler(scene):
    global landmarks_state_pre, landmarks_active_pre
    lm_obj = scene.objects.get("facial_landmarks")
    landmarks_active_post = False
    if lm_obj:
        landmarks_active_post = not (lm_obj.hide_viewport or lm_obj.hide_get())
    if landmarks_active_post:
        if landmarks_state_pre != 3 and lm_obj["state"] == 3:
            active_area = bpy.context.area
            region_3d = active_area.spaces.active.region_3d
            set_front_view(region_3d, view_selected=False)
    else:
        if landmarks_active_pre:
            unlock_3d_view()
            landmarks_active_pre = False


@persistent
def faceit_undo_pre_handler(scene):
    global landmarks_state_pre, landmarks_active_pre
    lm_obj = scene.objects.get("facial_landmarks")
    landmarks_active_pre = False
    if lm_obj:
        landmarks_active_pre = not (lm_obj.hide_viewport or lm_obj.hide_get())
        landmarks_state_pre = lm_obj["state"]


def set_default_vertex_groups(scene):
    objects = get_faceit_objects_list()
    for grp in FACEIT_VERTEX_GROUPS:
        item = scene.faceit_vertex_groups.get(grp)
        if item is None:
            # if grp not in scene.faceit_vertex_groups:
            item = scene.faceit_vertex_groups.add()
            item.name = grp
        # evaluate assign state
        for obj in objects:
            if item.name in obj.vertex_groups:
                item.is_assigned = True
                item.assign_object(obj.name)
    # add unassigned value
    item = scene.faceit_vertex_groups.get('UNASSIGNED')
    if item is None:
        item = scene.faceit_vertex_groups.add()
        item.name = 'UNASSIGNED'


@persistent
def faceit_load_handler(scene):
    bpy.ops.faceit.subscribe_settings()
    scene = bpy.context.scene
    if not scene.faceit_shapes_generated and scene.faceit_face_objects:
        bpy.ops.faceit.load_bake_modifiers("EXEC_DEFAULT", object_target='ALL')
    set_default_vertex_groups(scene)


def register():
    if faceit_scene_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(faceit_scene_update_handler)
    if faceit_load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(faceit_load_handler)
    if faceit_undo_pre_handler not in bpy.app.handlers.undo_pre:
        bpy.app.handlers.undo_pre.append(faceit_undo_pre_handler)
    if faceit_undo_post_handler not in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.append(faceit_undo_post_handler)
    # Subscribe to the active object for the current file.


def unregister():
    if faceit_scene_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(faceit_scene_update_handler)
    if faceit_load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(faceit_load_handler)
    if faceit_undo_post_handler in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.remove(faceit_undo_post_handler)
    if faceit_undo_pre_handler in bpy.app.handlers.undo_pre:
        bpy.app.handlers.undo_pre.remove(faceit_undo_pre_handler)
