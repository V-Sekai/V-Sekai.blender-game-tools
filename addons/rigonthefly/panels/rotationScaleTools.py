import bpy

from .main import ToolPanel, separator
#from ..operators import info
from ..core.icon_manager import Icons


class RotationScaleToolsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_rotationScaleTools'
    bl_label = 'Rotation & Scale Tools'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        layout.menu(RotationModeAndRelations_MT_Panel.bl_idname, icon='ORIENTATION_GIMBAL')

        row = layout.row(align=True)
        inheritRotationON = row.operator('rotf.inherit_rotation', text="On")
        inheritRotationON.inheritRotation = True
        inheritRotationOFF =  row.operator('rotf.inherit_rotation', text="Off")
        inheritRotationOFF.inheritRotation = False
        row = row.row(align=True)
        row.scale_x = 1.4
        row.label(text="Inherit Rotation")

        row = layout.row(align=True)
        inheritScaleON = row.operator('rotf.inherit_scale', text="On")
        inheritScaleON.inheritScale = True
        inheritScaleOFF = row.operator('rotf.inherit_scale', text="Off")
        inheritScaleOFF.inheritScale = False
        row = row.row(align=True)
        row.scale_x = 1.4
        row.label(text="Inherit Scale")

        row = layout.row(align=True)
        subRow = row.row(align=True)
        subRow.scale_y = 2
        subRow.operator('rotf.rotation_distribution', text="Distribute", icon='STRANDS')
        col = row.column(align=True)
        col.prop(bpy.context.scene, "rotf_rotation_distribution_chain_length")
        col.operator('rotf.apply_rotation_distribution', text="Apply")
        


class RotationModeAndRelations_MT_Panel(bpy.types.Menu):
    bl_label = "   Rotation Mode"
    bl_idname = "ROTF_MT_RotationModeAndRelationsMenu"

    def draw(self, context):
        layout = self.layout

        quaternion = layout.operator('rotf.rotation_mode', text="Quaternion")
        quaternion.rotationMode = 'QUATERNION'
        xyz = layout.operator('rotf.rotation_mode', text="XYZ")
        xyz.rotationMode = 'XYZ'
        xzy = layout.operator('rotf.rotation_mode', text="XZY")
        xzy.rotationMode = 'XZY'
        yxz = layout.operator('rotf.rotation_mode', text="YXZ")
        yxz.rotationMode = 'YXZ'
        yzx = layout.operator('rotf.rotation_mode', text="YZX")
        yzx.rotationMode = 'YZX'
        zxy = layout.operator('rotf.rotation_mode', text="ZXY")
        zxy.rotationMode = 'ZXY'
        zyx = layout.operator('rotf.rotation_mode', text="ZYX")
        zyx.rotationMode = 'ZYX'

class RotationScaleTools_CS_Panel(ToolPanel, bpy.types.Panel):
    bl_parent_id = "VIEW3D_PT_rotf_rotationScaleTools"
    bl_idname = "VIEW3D_PT_rotf_rotationScaleToolsCS"
    bl_label = "Controller Shapes Settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=False)
        row.label(text='Distribute')
        row.scale_x = 2
        row.prop(context.scene, 'rotf_rotationDistribution_customShape', text='')