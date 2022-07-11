import bpy

from .main import ToolPanel, separator
from ..core.icon_manager import Icons


class ArmatureToolsPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_armatureTools'
    bl_label = 'Armature Tools'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        selectedObjects = bpy.context.selected_objects
        selectedPBones = bpy.context.selected_pose_bones

        row = layout.row(align=True)
        row.operator('rotf.base_controller_shape', text="Basic Setup", icon='CON_SPLINEIK')

        row = layout.row(align=True)
        row.operator('rotf.bake_rig', text="Bake Rig", icon='OUTLINER_OB_ARMATURE')

        row = layout.row(align=True)
        proxyRow = row.row(align=True)
        proxyRow.operator('rotf.proxy', text="Proxy", icon='OUTLINER_DATA_ARMATURE')
        proxyRow = ProxyCondition(selectedObjects)
        row.operator('rotf.orient', text="Orient Visible", icon='ARMATURE_DATA')
        
        row = layout.row(align=True)
        row.operator('rotf.add_bone', text="Add Bone", icon='SORTBYEXT')

        row = layout.row(align=True)
        rootMotionRow = row.row(align=True)
        rootMotionRow.operator('rotf.root_motion', text="Root Motion", icon='TRANSFORM_ORIGINS')
        rootMotionRow.enabled = RootMotionCondition(selectedObjects)
        removeRootMotionRow = row.row(align=True)
        removeRootMotionRow.operator('rotf.remove_root_motion', text="Remove")
        removeRootMotionRow.enabled = RemoveRootMotionCondition(selectedPBones)
        
        row = layout.row(align=True)
        row.operator('rotf.center_of_mass', text="Center of Mass")
        row.operator('rotf.remove_center_of_mass', text="Remove")

class ArmatureTools_CS_Panel(ToolPanel, bpy.types.Panel):
    bl_parent_id = "VIEW3D_PT_rotf_armatureTools"
    bl_idname = "VIEW3D_PT_rotf_armatureToolsCS"
    bl_label = "Controller Shapes Settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=False)
        row.label(text='Base')
        row.scale_x = 2
        row.prop(context.scene, 'rotf_base_customShape', text='')

        layout = self.layout
        row = layout.row(align=False)
        row.label(text='Extra Bone')
        row.scale_x = 2
        row.prop(context.scene, 'rotf_extraBone_customShape', text='')

        layout = self.layout
        row = layout.row(align=False)
        row.label(text='Center of Mass')
        row.scale_x = 2
        row.prop(context.scene, 'rotf_centerOfMass_customShape', text='')

        layout = self.layout
        row = layout.row(align=False)
        row.label(text='Orient')
        row.scale_x = 2
        row.prop(context.scene, 'rotf_orient_customShape', text='')

        row = layout.row(align=False)
        row.label(text='Proxy')
        row.scale_x = 2
        row.prop(context.scene, 'rotf_proxy_customShape', text='')

        row = layout.row(align=False)
        row.label(text='Root Motion')
        row.scale_x = 2
        row.prop(context.scene, 'rotf_rootMotion_customShape', text='')

def ProxyCondition(selectedObjects):
    canProxy = False
    for obj in selectedObjects:
        #if obj.proxy or obj.override_library:
        if obj.override_library:
            canProxy = True
    return canProxy

def RootMotionCondition(selectedObjects):
    canRootMotion = True
    for obj in selectedObjects:
        if "Root Motion|" in obj.rotf_rig_state:
            canRootMotion = False
    return canRootMotion

def RemoveRootMotionCondition(selectedPBones):
    canRemoveRootMotion = False
    if bpy.context.mode == 'POSE':
        for pbone in selectedPBones:
            if 'ROOT' in pbone.bone.rotf_pointer_list:
                canRemoveRootMotion = True
    return canRemoveRootMotion