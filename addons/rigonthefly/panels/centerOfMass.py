import bpy

from .main import ToolPanel, separator
from ..core.icon_manager import Icons


class CenterOfMassPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_com'
    bl_label = 'Center of Mass'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        selectedObjects = bpy.context.selected_objects
        selectedPBones = bpy.context.selected_pose_bones
        activePoseBone = bpy.context.active_pose_bone

        row = layout.row(align=True)
        row.operator('rotf.center_of_mass', text="Center of Mass", icon='PROP_OFF')
        row.operator('rotf.remove_center_of_mass', text="Remove CoM")
        row = layout.row(align=True)
        row.operator('rotf.add_to_center_of_mass', text="Add to CoM")
        row.operator('rotf.remove_from_center_of_mass', text="Remove from CoM")

        col = layout.column(align=True)
        col.label(text="Influence List: "+activePoseBone.name)
        for key, value in activePoseBone.items():
            if "Weight" in key:
                keyName = '["'+key+'"]'
                col.prop(activePoseBone, keyName)

class CenterOfMass_CS_Panel(ToolPanel, bpy.types.Panel):
    bl_parent_id = "VIEW3D_PT_rotf_com"
    bl_idname = "VIEW3D_PT_rotf_comCS"
    bl_label = "Controller Shapes Settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=False)
        row.label(text='Center of Mass')
        row.scale_x = 2
        row.prop(context.scene, 'rotf_centerOfMass_customShape', text='')

def CoMCondition(activePoseBone):
    canCoM = False
    if activePoseBone == "Is center of mass bone":
        canCoM = True
    return canCoM