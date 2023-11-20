
import bmesh
import bpy
from bpy.props import BoolProperty, StringProperty


from ..shape_keys.corrective_shape_keys_utils import CORRECTIVE_SK_ACTION_NAME
from ..core.vgroup_utils import get_verts_in_vgroup
from ..core.modifier_utils import get_modifiers_of_type
from ..panels.draw_utils import draw_text_block
from ..core.pose_utils import is_pb_in_rest_pose
from ..core import faceit_utils as futils
from ..core import mesh_utils

WARNINGS_OUT = {
    'MIRROR': 'Object holds a MIRROR modifier. This can lead to problems in binding and/or baking! You should apply it first. If you need to preserve shape keys, check out the \'Apply Modifiers\' operator in bake tab/extra utils.',
    'MAIN_GROUP': 'The Main vertex group should only be assigned to one connected surface. Please make sure that the vertex group \'faceit_main\' only contains linked vertices (vertices that are connected by edges)! Use the Select Linked operator in Edit Mode to ensure connected surfaces are selected and click the Main button again. ',
    'MULTIPLE_MAIN': 'This object among others has the Main vertex group assigned. Please make sure that the vertex group \'faceit_main\' is only assigned to one object. ',
    'TRANSFORMS_ANIM': 'The Object has animation keyframes on transform channels. This might leat to problems in binding. Clear the keyframes or disable the action.',
    'ARMATURE_POSITION': 'The Object is bound to another armature. This can lead to problems in binding. Put the armature to Rest Position (before creating the landmarks!).',
    'SURFACE_DEFORM': 'The Object is bound to another object with a Surface Deform modifier. Either remove the binding / modifier or register the source object instead of this object.',
    'SHAPEKEYS': 'The Object has animated shape keys. This can lead to unexpected behaviour during baking. Consider to remove the action for animated shape keys or even setting the shape keys to their default values.',
}


def all_verts_in_main_group(obj):
    '''Check if any vertices in @obj are assigned to faceit_main'''
    vg = obj.vertex_groups.get('faceit_main')
    if vg:
        for v in obj.data.vertices:
            if any(g.group == vg.index for g in v.groups):
                continue
            return False
        return True
    return False


def get_island_count_in_main_group(obj):
    '''Return the count of individual islands assigned to the main group'''
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    vs = get_verts_in_vgroup(obj, 'faceit_main')
    if not vs:
        return 0
    vs_idx = [v.index for v in vs]
    bm_verts = [v for v in bm.verts if v.index in vs_idx]
    geo_islands = mesh_utils.GeometryIslands(bm_verts)
    island_count = geo_islands.get_island_count()
    bm.free()
    return island_count


def check_warnings_for_face_item(item):
    obj = item.get_object()
    all_warnings = []
    rig = futils.get_faceit_armature()
    if not bpy.context.scene.faceit_shapes_generated:
        if not futils.using_rigify_armature():
            if 'faceit_main' in obj.vertex_groups:
                if get_island_count_in_main_group(obj) > 1:
                    all_warnings.append('MAIN_GROUP')
                if any(_item.get_object().vertex_groups.get('faceit_main')
                       for _item in bpy.context.scene.faceit_face_objects if _item.name != item.name):
                    all_warnings.append('MULTIPLE_MAIN')
        if get_modifiers_of_type(obj, 'MIRROR'):
            all_warnings.append('MIRROR')
        for mod in obj.modifiers:
            if not mod.show_viewport:
                continue
            if 'ARMATURE_POSITION' not in all_warnings:
                if mod.type == 'ARMATURE':
                    rig_target = mod.object
                    if rig_target != rig and rig_target is not None:
                        if not rig_target.data.pose_position == 'REST':
                            if not all([is_pb_in_rest_pose(pb) for pb in rig_target.pose.bones]):
                                all_warnings.append('ARMATURE_POSITION')
            if 'SURFACE_DEFORM' not in all_warnings:
                if mod.type == 'SURFACE_DEFORM':
                    all_warnings.append('SURFACE_DEFORM')
                    break
        shape_keys = obj.data.shape_keys
        if shape_keys:
            if shape_keys.animation_data:
                action = shape_keys.animation_data.action
                if action:
                    if action.name != CORRECTIVE_SK_ACTION_NAME:
                        for fc in action.fcurves:
                            if fc.data_path.startswith('key_blocks') and 'faceit_cc_' not in fc.data_path:
                                if any(kf.co.y != 0.0 for kf in fc.keyframe_points):
                                    all_warnings.append('SHAPEKEYS')
                                    break
        if getattr(obj, 'animation_data'):
            if getattr(obj.animation_data, 'action'):
                for fc in obj.animation_data.action.fcurves:
                    if any(a in fc.data_path
                            for a in ['location', 'scale', 'rotation_euler', 'rotation_quaternion']):
                        all_warnings.append('TRANSFORMS_ANIM')
                        break
    item.warnings = ''
    if all_warnings:
        for warn in all_warnings:
            item.warnings += warn + ','
    return all_warnings


class FACEIT_OT_CheckWarning(bpy.types.Operator):
    '''There are Warnings for this object'''
    bl_idname = 'faceit.face_object_warning_check'
    bl_label = 'Check Warnings'
    bl_options = {'INTERNAL'}

    # the name of the facial part
    item_name: StringProperty(options={'SKIP_SAVE'})

    set_show_warnings: BoolProperty(options={'SKIP_SAVE'})

    check_main: BoolProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        scene = context.scene
        if self.item_name == 'ALL':
            items = scene.faceit_face_objects
        else:
            items = [scene.faceit_face_objects[self.item_name]]
        any_warning = False
        for item in items:
            all_warnings = check_warnings_for_face_item(item)
            if all_warnings:
                any_warning = True
                for warn in all_warnings:
                    self.report({'WARNING'}, f'[{item.name}]: {WARNINGS_OUT[warn]}')
        if any_warning:
            if self.set_show_warnings:
                scene.faceit_show_warnings = True
        else:
            scene.faceit_show_warnings = False
            self.report({'INFO'}, 'No Warnings found.')
        if not futils.using_rigify_armature():
            if not any('faceit_main' in obj.vertex_groups for obj in futils.get_faceit_objects_list()):
                self.report({'WARNING'}, 'Main Face Vertex Island could not be found. Please assign the Main Vertex Group!')
        return {'FINISHED'}


class FACEIT_OT_DisplayWarning(bpy.types.Operator):
    '''There are Warnings for this object'''
    bl_idname = 'faceit.face_object_warning'
    bl_label = 'Faceit Geometry Warnings'
    bl_options = {'INTERNAL'}

    item_name: StringProperty(name='Item Name')

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='WARNINGS')
        row = layout.row(align=True)
        web = row.operator('faceit.open_web', text='Prepare Geometry', icon='QUESTION')
        web.link = 'https://faceit-doc.readthedocs.io/en/latest/prepare/'
        layout.separator()
        item = context.scene.faceit_face_objects[self.item_name]
        warnings = item.warnings.split(',')

        for warn in warnings:
            if warn:
                warning_message = WARNINGS_OUT[warn]
                draw_text_block(layout=layout, text=warning_message,
                                heading=warn.replace('_', ' '), heading_icon='ERROR')  # code=solution_popover)
                if warn in ('MIRROR', 'SURFACE_DEFORM'):
                    row = layout.row()
                    op = row.operator("faceit.apply_modifier_object_with_shape_keys", icon='CHECKMARK')
                    op.obj_name = item.name
                    op.check_warnings = True
                if warn == 'ARMATURE_POSITION':
                    other_rigs = []
                    obj = item.get_object()
                    for mod in obj.modifiers:
                        if mod.type == 'ARMATURE':
                            rig_target = mod.object
                            if rig_target != context.scene.faceit_armature and rig_target is not None:
                                if not rig_target.data.pose_position == 'REST':
                                    if not all([is_pb_in_rest_pose(pb) for pb in rig_target.pose.bones]):
                                        other_rigs.append(rig_target)
                    for rig in other_rigs:
                        row = layout.row()
                        row.prop(rig, 'name', text='Armature')
                        row = layout.row()
                        op = row.operator("faceit.set_body_bind_pose", icon='LOOP_BACK')
                        op.rig_name = rig.name
                        op.check_warnings = True
                        row = layout.row()
                        row.prop(rig.data, "pose_position", text="Pose Position", expand=True)
                if warn == 'SHAPEKEYS':
                    row = layout.row()
                    op = row.operator('faceit.clear_shape_key_action', text='Clear Shape Key Action', icon='ACTION')
                    op.obj_name = item.name

    def invoke(self, context, event):
        item = context.scene.faceit_face_objects[self.item_name]
        if not check_warnings_for_face_item(item):
            self.report({'INFO'}, 'No Warnings found.')
            return {'FINISHED'}
        else:
            wm = context.window_manager
            return wm. invoke_popup(self)

    def execute(self, context):
        return {'FINISHED'}
