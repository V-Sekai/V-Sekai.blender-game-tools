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

        bakeRigRow = layout.row(align=True)
        bakeRigRow.operator('rotf.bake_rig', text="Bake Rig", icon='OUTLINER_OB_ARMATURE')
        bakeRigRow.enabled = BakeRigCondition(selectedObjects)

        row = layout.row(align=True)
        proxyRow = row.row(align=True)
        proxyRow.operator('rotf.proxy', text="Proxy", icon='OUTLINER_DATA_ARMATURE')
        proxyRow.enabled = ProxyCondition(selectedObjects)
        removeProxyRow = row.row(align=True)
        removeProxyRow.operator('rotf.remove_proxy', text="Remove Proxy")
        removeProxyRow.enabled = RemoveProxyCondition(selectedObjects)

        row = layout.row(align=True)
        orientRow = row.row(align=True)
        orientRow.operator('rotf.orient', text="Orient Visible", icon='ARMATURE_DATA')
        orientRow.prop(context.scene, "rotf_orient_mirror", text='Mirror Orient')
        orientRow.enabled = OrientCondition(selectedObjects)
        
        row = layout.row(align=True)
        row.operator('rotf.add_bone', text="Add Bone", icon='SORTBYEXT')

        row = layout.row(align=True)
        rootMotionRow = row.row(align=True)
        rootMotionRow.operator('rotf.root_motion', text="Root Motion", icon='TRANSFORM_ORIGINS')
        rootMotionRow.enabled = RootMotionCondition(selectedObjects)
        removeRootMotionRow = row.row(align=True)
        removeRootMotionRow.operator('rotf.remove_root_motion', text="Remove RM")
        removeRootMotionRow.enabled = RemoveRootMotionCondition(selectedPBones)

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

def BakeRigCondition(selectedObjects):
    canBakeRig = False
    for obj in selectedObjects:
        if obj.get('rotf_rig_state'):
            canBakeRig = True
    return canBakeRig

def ProxyCondition(selectedObjects):
    canProxy = False
    for obj in selectedObjects:
        #if obj.proxy or obj.override_library:
        if obj.override_library:
            canProxy = True
    return canProxy

def RemoveProxyCondition(selectedObjects):
    canRemoveProxy = False
    for obj in selectedObjects:
        #if obj.proxy or obj.override_library:
        if obj.rotf_copy_of_proxy:
            canRemoveProxy = True
    return canRemoveProxy

def OrientCondition(selectedObjects):
    canOrient = False
    for obj in selectedObjects:
        if obj.type == 'ARMATURE':
            canOrient = True
    return canOrient

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