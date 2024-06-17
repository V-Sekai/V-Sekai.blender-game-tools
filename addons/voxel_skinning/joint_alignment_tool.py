import bpy
import mathutils
from bpy.props import *

class JAT_Surface_OT_Operator(bpy.types.Operator):
    """Align selected joints to mesh surface along current view"""
    bl_idname = "wm.joint_alignment_tool_surface"
    bl_label = "Align Selected Joints To Mesh Surface"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        if not (context.active_object != None and context.active_object.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'):
            self.report({'ERROR'}, "Please select one armature and enter 'EDIT' mode, then try again.")
            return {'CANCELLED'}

        area = next(area for area in context.window.screen.areas if area.type == 'VIEW_3D')
        if area.spaces.active.region_3d.is_perspective:
            self.report({'ERROR'}, "Please switch to orthogonal view, then try again.")
            return {'CANCELLED'}

        _, rot, _ = area.spaces.active.region_3d.view_matrix.inverted().decompose()
        ray_cast_dir = rot @ mathutils.Vector((0, 0, -1))
        ob = context.active_object
        amt = ob.data
        loc_dic = {}
        for bone in amt.edit_bones:
            if bone.select_head:
                world_bone_head = ob.matrix_world @ bone.head
                ray_start = world_bone_head - ray_cast_dir * 100.0
                while True:
                    if bpy.app.version < (2, 91):
                        hit, loc, _, _, obj, mw = context.scene.ray_cast(context.view_layer, ray_start, ray_cast_dir)
                    else:
                        hit, loc, _, _, obj, mw = context.scene.ray_cast(context.view_layer.depsgraph, ray_start, ray_cast_dir)
                    if not hit:
                        break
                    if obj.type != 'MESH':
                        ray_start = loc + ray_cast_dir * 0.0001
                        continue
                    loc_dic[(bone, "head")] = ob.matrix_world.inverted_safe() @ loc
                    break
            if bone.select_tail:
                world_bone_tail = ob.matrix_world @ bone.tail
                ray_start = world_bone_tail - ray_cast_dir * 100.0
                while True:
                    if bpy.app.version < (2, 91):
                        hit, loc, _, _, obj, mw = context.scene.ray_cast(context.view_layer, ray_start, ray_cast_dir)
                    else:
                        hit, loc, _, _, obj, mw = context.scene.ray_cast(context.view_layer.depsgraph, ray_start, ray_cast_dir)
                    if not hit:
                        break
                    if obj.type != 'MESH':
                        ray_start = loc + ray_cast_dir * 0.0001
                        continue
                    loc_dic[(bone, "tail")] = ob.matrix_world.inverted_safe() @ loc
                    break
        for bone in amt.edit_bones:
            if bone.select_head:
                if (bone, "head") in loc_dic:
                    bone.head = loc_dic[(bone, "head")]
            if bone.select_tail:
                if (bone, "tail") in loc_dic:
                    bone.tail = loc_dic[(bone, "tail")]
        return {'FINISHED'}


def init_properties():
    pass

def clear_properties():
    pass

class JAT_Volume_OT_Operator(bpy.types.Operator):
    """Align selected joints to mesh volume along current view"""
    bl_idname = "wm.joint_alignment_tool_volume"
    bl_label = "Align Selected Joints To Mesh Volume"
    bl_options = {'REGISTER', 'UNDO'}


    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        if not (context.active_object != None and context.active_object.type == 'ARMATURE' and context.mode == 'EDIT_ARMATURE'):
            self.report({'ERROR'}, "Please select one armature and enter 'EDIT' mode, then try again.")
            return {'CANCELLED'}

        area = next(area for area in context.window.screen.areas if area.type == 'VIEW_3D')
        if area.spaces.active.region_3d.is_perspective:
            self.report({'ERROR'}, "Please switch to orthogonal view, then try again.")
            return {'CANCELLED'}

        _, rot, _ = area.spaces.active.region_3d.view_matrix.inverted().decompose()
        ray_cast_dir = rot @ mathutils.Vector((0, 0, -1))
        ob = context.active_object
        amt = ob.data
        loc_dic = {}
        for bone in amt.edit_bones:
            if bone.select_head:
                world_bone_head = ob.matrix_world @ bone.head
                ray_start = world_bone_head - ray_cast_dir * 100.0
                first_hit = False
                first_loc = None
                last_loc = None
                hit_count = 0
                while True:
                    if bpy.app.version < (2, 91):
                        hit, loc, _, _, obj, mw = context.scene.ray_cast(context.view_layer, ray_start, ray_cast_dir)
                    else:
                        hit, loc, _, _, obj, mw = context.scene.ray_cast(context.view_layer.depsgraph, ray_start, ray_cast_dir)
                    if not hit:
                        break
                    if obj.type != 'MESH':
                        ray_start = loc + ray_cast_dir * 0.0001
                        continue
                    loc_dic[(bone, "head")] = ob.matrix_world.inverted_safe() @ loc
                    if not first_hit:
                        first_hit = True
                        first_loc = loc_dic[(bone, "head")]
                    last_loc = loc_dic[(bone, "head")]
                    hit_count += 1
                    if hit_count >= context.scene.jat_max_raycast_hit_count:
                        break
                    ray_start = loc + ray_cast_dir * 0.0001
                if first_hit:
                    loc_dic[(bone, "head")] = (first_loc + last_loc) * 0.5
            if bone.select_tail:
                world_bone_tail = ob.matrix_world @ bone.tail
                ray_start = world_bone_tail - ray_cast_dir * 100.0
                first_hit = False
                first_loc = None
                last_loc = None
                hit_count = 0
                while True:
                    if bpy.app.version < (2, 91):
                        hit, loc, _, _, obj, mw = context.scene.ray_cast(context.view_layer, ray_start, ray_cast_dir)
                    else:
                        hit, loc, _, _, obj, mw = context.scene.ray_cast(context.view_layer.depsgraph, ray_start, ray_cast_dir)
                    if not hit:
                        break
                    if obj.type != 'MESH':
                        ray_start = loc + ray_cast_dir * 0.0001
                        continue
                    loc_dic[(bone, "tail")] = ob.matrix_world.inverted_safe() @ loc
                    if not first_hit:
                        first_hit = True
                        first_loc = loc_dic[(bone, "tail")]
                    last_loc = loc_dic[(bone, "tail")]
                    hit_count += 1
                    if hit_count >= context.scene.jat_max_raycast_hit_count:
                        break
                    ray_start = loc + ray_cast_dir * 0.0001
                if first_hit:
                    loc_dic[(bone, "tail")] = (first_loc + last_loc) * 0.5
        for bone in amt.edit_bones:
            if bone.select_head:
                if (bone, "head") in loc_dic:
                    bone.head = loc_dic[(bone, "head")]
            if bone.select_tail:
                if (bone, "tail") in loc_dic:
                    bone.tail = loc_dic[(bone, "tail")]
        return {'FINISHED'}


def init_properties():
    bpy.types.Scene.jat_max_raycast_hit_count = IntProperty(
        name = "Max Raycast Hit Count",
        description = "Max raycast hit count to detect mesh volume, you can try a bigger number if the mesh part is not manifold, but too big number might cause interference from other mesh parts",
        default = 2,
        min = 2,
        max = 1024)


def clear_properties():
    props = ["jat_max_raycast_hit_count"]

    for p in props:
        if p in bpy.types.Scene.bl_rna.properties:
            exec("del bpy.types.Scene." + p)

class JAT_PT_JointAlignmentPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Joint Alignment Tool"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Mesh Online'

    @classmethod
    def poll(self, context):
        return True


    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Surface Mode")
        row = layout.row()
        row.operator("wm.joint_alignment_tool_surface")
        row = layout.row()
        row.label(text="Volume Mode")
        layout.prop(context.scene, 'jat_max_raycast_hit_count', icon='BLENDER', toggle=True)
        row = layout.row()
        row.operator("wm.joint_alignment_tool_volume")


def register_joint_alignment_tool():
    bpy.utils.register_class(JAT_PT_JointAlignmentPanel)
    bpy.utils.register_class(JAT_Surface_OT_Operator)
    bpy.utils.register_class(JAT_Volume_OT_Operator)
    init_properties()


def unregister_joint_alignment_tool():
    bpy.utils.unregister_class(JAT_PT_JointAlignmentPanel)
    bpy.utils.unregister_class(JAT_Surface_OT_Operator)
    bpy.utils.unregister_class(JAT_Volume_OT_Operator)
    clear_properties()


if __name__ == "__main__":
    register_joint_alignment_tool()
