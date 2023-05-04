bl_info = {
    "name": "QOL_SnapOffCopy",
    "author": "Rico Holmes",
    "version": (1, 0, 0),
    "blender": (3, 00, 0),
    "description": "Allows you to snap off components to a new object",
    "category": "Object",
    }

import bpy
from .prefs import *
from bpy.types import (Operator,)
from bpy.props import *

class QOL_SnapOffCopy(Operator):
    bl_idname = "object.qol_snapoffcopy"
    bl_label = "Snap Off Copy"
    bl_description = "Snaps off a component to a new object"
    bl_options = {'REGISTER', 'UNDO'}

    pivotToSelf: BoolProperty(
        name="Pivot to Self",
        description="Pivots the new object to the center of the original object",
        default = True
        )
        
    stayInEditMode: BoolProperty(
        name="Stay in Edit Mode",
        description="Stays in edit mode after the operation",
        default=True
    )

    @classmethod
    def poll(cls, context):
        return context.active_object != None and context.active_object.type == 'MESH' and context.active_object.mode == 'EDIT'

    def invoke(self, context, event):
        print ("QOL_SnapOffCopy evoked")
        self.pivotToSelf = context.preferences.addons[__package__].preferences.pivotToSelf
        self.stayInEditMode = context.preferences.addons[__package__].preferences.stayInEditMode
        return self.execute(context)

    def execute(self, context):
        modeType = bpy.context.tool_settings.mesh_select_mode
        objects_before = {o for o in bpy.data.objects}
        bpy.ops.mesh.duplicate_move(MESH_OT_duplicate={"mode":1}, TRANSFORM_OT_translate={"value":(0, 0, 0),"use_automerge_and_split":False})
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.duplicates_make_real()
        created_objects = {o for o in bpy.data.objects}.difference(objects_before)
        new_obj = created_objects.pop()
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        bpy.context.view_layer.objects.active = new_obj
        if self.pivotToSelf:
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        if self.stayInEditMode:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles()
            bpy.context.tool_settings.mesh_select_mode = modeType

        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "pivotToSelf")
        layout.prop(self, "stayInEditMode")


def draw(self, context):
    self.layout.operator("object.qol_snapoffcopy", text="QOL Snap Off Copy")

def register():
    bpy.utils.register_class(RH_SnapOffCopy_preferences)
    bpy.utils.register_class(QOL_SnapOffCopy)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(draw)

def unregister():
    bpy.utils.unregister_class(RH_SnapOffCopy_preferences)
    bpy.utils.unregister_class(QOL_SnapOffCopy)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(draw)

if __name__ == "__main__":
    register()

        