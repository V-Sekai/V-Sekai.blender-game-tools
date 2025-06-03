import bpy

from .main import ToolPanel, separator
from ..core.icon_manager import Icons

class SpaceSwitchPanel(ToolPanel, bpy.types.Panel):

    bl_idname = 'VIEW3D_PT_rotf_spaceSwitch'
    bl_label = 'Space Switch'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        selectedPBoneList = bpy.context.selected_pose_bones
        activePBone = bpy.context.active_pose_bone

        scene = context.scene
        layout = self.layout

        hasWorld = WorldCondition(selectedPBoneList)

        canParent, canParentCopy, canRemoveParent = ParentCondition(selectedPBoneList, activePBone)
        
        hasReverse = ReverseHierarchyCondition(selectedPBoneList)

        #WORLD SPACE
        row = layout.row(align=True)
        row.label(text="World:")
        row = layout.row(align=True)
        worldSubRow = row.row(align=True)
        worldSubRow.operator('rotf.world_space', text="Make World", icon='ORIENTATION_GLOBAL')
        worldSubRow.enabled = not hasWorld
        removeWorldSubRow = row.row(align=True)
        removeWorldSubRow.operator('rotf.remove_world_space', text="Remove World") #, icon='OBJECT_ORIGIN')
        removeWorldSubRow.enabled = hasWorld

        #AIM SPACE
        row = layout.row(align=True)
        row.label(text="Aim:")
        row = layout.row(align=True)
        #row.prop(scene, 'rotf_aim_stretch', text="Stretch")
        row.prop(scene, 'rotf_aim_axis')
        #row = layout.row(align=True)
        row.prop(scene, 'rotf_aim_distance', text="Distance")

        row = layout.row(align=True)
        row.operator('rotf.aim_space', text="Make Aim", icon='CON_TRACKTO')
        row.operator('rotf.aim_offset_space', text="Aim Offset", icon='MOD_SIMPLIFY')
        row = layout.row(align=True)
        row.operator('rotf.remove_aim_space', text="Remove Aim")

        #PARENT SPACE
        row = layout.row(align=True)
        row.label(text="Parent:")
        col = layout.column(align=True)
        row = col.row(align=True)
        parentRow = row.row(align=True)
        parentRow.operator('rotf.parent_space', text="Parent", icon='PIVOT_ACTIVE')
        parentRow.enabled = canParent
        parentCopyRow = row.row(align=True)
        parentCopyRow.operator('rotf.parent_copy_space', text="Parent Copy", icon='PIVOT_INDIVIDUAL')
        parentCopyRow.enabled = canParentCopy
        row = col.row(align=True)
        row.operator('rotf.parent_offset_space', text="Parent Offset", icon='PIVOT_CURSOR')
        row = col.row(align=True)
        row.operator('rotf.remove_parent_space', text="Restore Child")
        row.operator('rotf.remove_parent_space_siblings', text="Restore Siblings")
        row.enabled = canRemoveParent

        #REVERSE HIERARCHY SPACE
        row = layout.row(align=True)
        row.label(text="Hierarchy:")
        row = layout.row(align=True)
        reverseRow = row.row(align=True)
        reverseRow.operator('rotf.reverse_hierarchy_space', text="Reverse", icon='UV_SYNC_SELECT')
        reverseRow.enabled = not hasReverse
        restoreReverseRow = row.row(align=True)
        restoreReverseRow.operator('rotf.restore_hierarchy_space', text="Restore")
        restoreReverseRow.enabled = hasReverse

class SpaceSwitch_CS_Panel(ToolPanel, bpy.types.Panel):
    bl_parent_id = "VIEW3D_PT_rotf_spaceSwitch"
    bl_idname = "VIEW3D_PT_rotf_spaceSwitchCS"
    bl_label = "Controller Shapes Settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        row = layout.row(align=False)
        row.label(text='World')
        row.scale_x = 2
        row.prop(scene, 'rotf_worldSpace_customShape', text='')

        row = layout.row(align=False)
        row.label(text='Aim')
        row.scale_x = 2
        row.prop(scene, 'rotf_aimSpace_customShape', text='')

        row = layout.row(align=False)
        row.label(text='Aim Target')
        row.scale_x = 2
        row.prop(scene, 'rotf_aimTarget_customShape', text='')

        row = layout.row(align=False)
        row.label(text='Parent')
        row.scale_x = 2
        row.prop(scene, 'rotf_parentSpace_customShape', text='')

        row = layout.row(align=False)
        row.label(text='Reverse')
        row.scale_x = 2
        row.prop(scene, 'rotf_reverseHierarchySpace_customShape', text='')

def ParentCondition(selectedPBoneList, activePBone):
    canParent = True
    canParentCopy = True
    canRemoveParent = False

    if bpy.context.mode == 'POSE':
        if len(selectedPBoneList) < 2 :
            canParent = False
            canParentCopy = False

        for pbone in selectedPBoneList:
            if 'CHILD' in pbone.bone.rotf_pointer_list:
                canRemoveParent = True
                if pbone != activePBone:
                    canParent = False
                    canParentCopy = False            
            
            if activePBone in pbone.children_recursive:
                canParent = False

    return canParent, canParentCopy, canRemoveParent

def WorldCondition(selectedPBoneList):
    hasWorld = False

    if bpy.context.mode == 'POSE':
        for pbone in selectedPBoneList:
            if 'WORLD' in pbone.bone.rotf_pointer_list:
                hasWorld = True

    return hasWorld

def ReverseHierarchyCondition(selectedPBoneList):
    hasReverseHierarchy = False

    if bpy.context.mode == 'POSE':
        for pbone in selectedPBoneList:
            if 'REVERSE' in pbone.bone.rotf_pointer_list:
                hasReverseHierarchy = True

    return hasReverseHierarchy
