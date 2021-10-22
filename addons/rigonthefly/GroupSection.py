#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility

class GroupSectionUtils:

    def GroupSection (self, context):
        savedState = StateUtility.SaveState()
        #force edit mode
        StateUtility.SetEditMode()

        #list selected bones and order them
        selectedRigBonesListE = list(bpy.context.selected_editable_bones)
        selectedRigBonesListE.sort(key = lambda x:len(x.parent_recursive))

        #execute DuplicateMerge function
        duplicateMergeBone = GroupSectionUtils.DuplicateMerge(selectedRigBonesListE,bpy)

        #save mode, selected editable bones and selected pose bones
        StateUtility.RecoverState(savedState)

    @staticmethod
    def DuplicateMerge (editableBonesList,bpy):
        #duplicates selected bones
        bpy.ops.armature.duplicate()
        #connect duplicated bones for merging
        for selectedBone in bpy.context.selected_editable_bones:
            selectedBone.use_connect = True
        #merges duplicated bones into one bone
        bpy.ops.armature.merge(type='WITHIN_CHAIN')
        #rename merged bone
        mergeBoneBaseName = editableBonesList[0].basename
        bpy.context.selected_editable_bones[0].name = editableBonesList[0].name.replace(mergeBoneBaseName,mergeBoneBaseName+"Section")
        #make merged bone roll same as top selected bone
        bpy.context.selected_bones[0].roll = editableBonesList[0].roll
        #set merged bone as parent to selected bones
        editableBonesList[0].parent = bpy.context.selected_editable_bones[0]

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #change merged bone display
        bpy.context.selected_pose_bones[0].custom_shape = bpy.data.objects["Circle"]

        #return bpy.context.selected_editable_bones[0]


