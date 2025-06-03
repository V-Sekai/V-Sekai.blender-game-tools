import bpy

from .main import ToolPanel, separator
from ..core.icon_manager import Icons

class IKFKSwitchPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_ikfkSwitch'
    bl_label = 'IK FK Switch'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        #if not self.DisplayCondition(context):
        #    return

        hasIK = False
        hasStretchIK = False
        if bpy.context.mode == 'POSE':
            for pbone in bpy.context.selected_pose_bones:
                if 'IK' in pbone.bone.rotf_pointer_list:
                    hasIK = True
                if 'IK_STRETCH' in pbone.bone.rotf_pointer_list:
                    hasStretchIK = True
                
        row = layout.row(align=True)
        row.label(text="Bend IK:")
        row = layout.row(align=True)
        row.label(text="IK Chain Length ")
        row.prop(context.scene, "rotf_bend_ik_chain_length")

        row = layout.row(align=True)
        row.scale_y = 1
        row.scale_x = 0.1
        row.label(text=("IK Stretch Type"))  # offset for ikStretch boolean box
        row.prop(context.scene, "rotf_bend_ik_stretch_type")

        row = layout.row(align=True)
        row.prop(context.scene, "rotf_bend_ik_pole_vector", text="Pole Vector")

        labelRow = row.row(align=True)
        labelRow.scale_x = 0.8
        labelRow.label(text="If Straight ")
        propRow = row.row(align=True)
        propRow.scale_x = 0.5
        propRow.prop(bpy.context.scene, "rotf_bend_ik_default_pole_axis")
        
        row = layout.row(align=True)
        row.scale_y = 1
        ikSubRow = row.row(align=True)
        ikSubRow.operator('rotf.ik_limb', text="IK", icon='CON_KINEMATIC')
        ikSubRow.enabled = not hasIK

        fkSubRow =  row.row(align=True)
        fkSubRow.operator('rotf.fk_limb', text="FK", icon='CON_ROTLIKE')
        fkSubRow.enabled = hasIK

        separator(layout, 0.50)
        row = layout.row(align=True)
        row.label(text="Stretch IK:")
        row = layout.row(align=True)
        row.label(text="IK Chain Length")
        row.prop(context.scene, "rotf_stretch_ik_chain_length")
        row = layout.row(align=True)
        row.label(text=("IK Stretch Type"))  # offset for ikStretch boolean box
        row.prop(context.scene, "rotf_stretch_ik_stretch_type")
        row = layout.row(align=True)
        row.prop(context.scene, "rotf_stretch_ik_distribute_rotation", text="Distribute Rotation")

        row = layout.row(align=True)
        ikSubRow = row.row(align=True)
        ikSubRow.operator('rotf.ik_stretch', text="Stretch IK", icon='CON_KINEMATIC')
        ikSubRow.enabled = not hasStretchIK
        removeIKSubRow = row.row(align=True)
        removeIKSubRow.operator('rotf.remove_ik_stretch', text="Remove", icon='CON_ROTLIKE')
        removeIKSubRow.enabled = hasStretchIK
        

class IKFKSwitch_CS_Panel(ToolPanel, bpy.types.Panel):
    bl_parent_id = "VIEW3D_PT_rotf_ikfkSwitch"
    bl_idname = "VIEW3D_PT_rotf_ikfkSwitchCS"
    bl_label = "Controller Shapes Settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=False)
        row.label(text='IK Target')
        row.scale_x = 2
        row.prop(context.scene, 'rotf_ikTarget_customShape', text='')

        row = layout.row(align=False)
        row.label(text='Pole Vector')
        row.scale_x = 2
        row.prop(context.scene, 'rotf_poleVector_customShape', text='')