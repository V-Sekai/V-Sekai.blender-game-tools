import bpy
from bpy.app.handlers import persistent
from ..rigging.pivot_manager import PivotManager
from ..core.faceit_utils import get_faceit_armature
from ..core.faceit_data import LIVE_MOCAP_DEFAULT_SETTINGS
from ..core.modifier_utils import populate_bake_modifier_items
from ..landmarks.landmarks_utils import is_landmarks_active, set_front_view, unlock_3d_view


landmarks_state_pre = 0
landmarks_active_pre = False
pivot_drawing_pre = False
rig_active_pre = False


@persistent
def faceit_scene_update_handler(scene):
    context = bpy.context
    faceit_objects = scene.faceit_face_objects
    if hasattr(context, "active_operator") and getattr(context.active_operator, "bl_idname", "") == "OBJECT_OT_delete":
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
        if faceit_objects:
            for obj_item in faceit_objects:
                if obj_item.name not in scene.objects:
                    index = scene.faceit_face_objects.find(obj_item.name)
                    scene.faceit_face_objects.remove(index)
    if PivotManager.is_drawing:
        lm_obj = scene.objects.get("facial_landmarks")
        if not is_landmarks_active(lm_obj):
            PivotManager.stop_drawing()
    if not scene.faceit_shapes_generated:
        if scene.faceit_expression_list and scene.faceit_workspace.active_tab in ('BAKE'):
            active_object = getattr(context, "active_object")
            if active_object is not None:
                populate_bake_modifier_items(objects=[active_object])


@persistent
def faceit_undo_post_handler(scene):
    lm_obj = scene.objects.get("facial_landmarks")
    landmarks_active_post = is_landmarks_active(lm_obj)
    if landmarks_active_post:
        context = bpy.context
        if context.preferences.addons["faceit"].preferences.use_vertex_size_scaling:
            context.preferences.themes[0].view_3d.vertex_size = context.preferences.addons["faceit"].preferences.landmarks_vertex_size
        if landmarks_state_pre != 3 and lm_obj["state"] == 3:
            co = round(lm_obj.data.vertices[0].co.y, 5)
            if all((round(v.co.y, 5) == co for v in lm_obj.data.vertices)):
                active_area = context.area
                region_3d = active_area.spaces.active.region_3d
                set_front_view(region_3d, view_selected=False)
            elif rig_active_pre:
                lm_obj["state"] = 4
        if lm_obj["state"] >= 4:
            PivotManager.start_drawing(context)
            dg = context.evaluated_depsgraph_get()
            lm_eval = lm_obj.evaluated_get(dg)
            me = lm_eval.to_mesh()
            print("evaluated vertices", len(me.vertices))
            if len(me.vertices) == 74:
                # hacky method to restore these properties.. but it works..
                # TODO: do the same thing for the redo handler..
                if scene.faceit_eye_pivot_placement == 'AUTO':
                    scene.faceit_eye_pivot_placement = 'MANUAL'

                if scene.faceit_eye_pivot_placement == 'MANUAL':
                    scene.faceit_eye_pivot_placement = 'AUTO'
    else:
        if landmarks_active_pre:
            unlock_3d_view()


@persistent
def faceit_undo_pre_handler(scene):
    global landmarks_state_pre, landmarks_active_pre, rig_active_pre
    lm_obj = scene.objects.get("facial_landmarks")
    landmarks_active_pre = False
    if lm_obj:
        # pivot_drawing_pre = PivotManager.is_drawing
        landmarks_active_pre = is_landmarks_active(lm_obj)
        landmarks_state_pre = lm_obj["state"]
        if get_faceit_armature(force_original=True) is not None:
            rig_active_pre = True


def register_mocap_engine_defaults(scene):
    for engine, values in LIVE_MOCAP_DEFAULT_SETTINGS.items():
        item = scene.faceit_live_mocap_settings.get(engine)
        if item is None:
            item = scene.faceit_live_mocap_settings.add()
            item.name = engine
            item.address = values.get('address', '0.0.0.0')
            item.port = values.get('port', 9001)
            item.rotation_units = values.get('rotation_units', 'DEG')
            item.head_location_multiplier = values.get('head_location_multiplier', 1.0)
        # Hard set constant values
        item.rotation_units_variable = values.get('rotation_units_variable', False)
        item.can_animate_head_rotation = values.get('can_animate_head_rotation', False)
        item.can_animate_head_location = values.get('can_animate_head_location', False)
        item.can_animate_eye_rotation = values.get('can_animate_eye_rotation', False)


def register_default_properties():
    ''' Handler that registers default properties for the scene and removes itself. '''
    scene = bpy.context.scene
    register_mocap_engine_defaults(scene)
    bpy.app.timers.unregister(register_default_properties)
    return 0.01


@persistent
def faceit_load_handler(scene):
    bpy.ops.faceit.subscribe_settings()
    scene = bpy.context.scene
    if not scene.faceit_shapes_generated and scene.faceit_face_objects:
        bpy.ops.faceit.load_bake_modifiers("EXEC_DEFAULT", object_target='ALL')
    register_mocap_engine_defaults(scene)
    lm_obj = scene.objects.get("facial_landmarks")
    if lm_obj:
        if bpy.context.active_object is lm_obj:
            if bpy.context.preferences.addons["faceit"].preferences.use_vertex_size_scaling:
                bpy.context.preferences.themes[0].view_3d.vertex_size = bpy.context.preferences.addons["faceit"].preferences.landmarks_vertex_size
        landmarks_active = not (lm_obj.hide_viewport or lm_obj.hide_get())
        PivotManager.initialize_pivots(bpy.context)
        if landmarks_active:
            if lm_obj["state"] >= 4:
                PivotManager.start_drawing(bpy.context)


@persistent
def faceit_save_pivots_handler(_scene):
    if PivotManager.is_drawing:
        PivotManager.save_pivots(bpy.context)


@persistent
def faceit_load_pre_hanlder(scene):
    PivotManager.stop_drawing()


def register():
    if faceit_scene_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(faceit_scene_update_handler)
    bpy.app.timers.register(register_default_properties)
    if faceit_load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(faceit_load_handler)
    if faceit_undo_pre_handler not in bpy.app.handlers.undo_pre:
        bpy.app.handlers.undo_pre.append(faceit_undo_pre_handler)
    if faceit_undo_post_handler not in bpy.app.handlers.undo_post:
        bpy.app.handlers.undo_post.append(faceit_undo_post_handler)
    if faceit_load_pre_hanlder not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(faceit_load_pre_hanlder)
    bpy.app.handlers.save_pre.append(faceit_save_pivots_handler)
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
    if faceit_load_pre_hanlder in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(faceit_load_pre_hanlder)
    bpy.app.handlers.save_pre.remove(faceit_save_pivots_handler)
