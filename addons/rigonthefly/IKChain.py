#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility

class IKChainUtils:

    def IKChain (self, context):
        savedState = StateUtility.SaveState()

        #force pose mode
        StateUtility.SetEditMode()

        #list selected bones and order them in edit mode
        selectedBonesList = bpy.context.selected_editable_bones.copy()
        selectedBonesList.sort(key = lambda x:len(x.parent_recursive))

        parentBoneN = selectedBonesList[0].parent.name
        print("parent bone "+parentBoneN)

        selectedBonesListN = []
        for b in selectedBonesList:
            selectedBonesListN.append(b.name)
        
        for b in selectedBonesListN:
            print("selected bone "+b)

        #execute IKHierarchy function
        IKChainUtils.IKHierarchy (selectedBonesListN,parentBoneN,bpy)

        #save mode, selected editable bones and selected pose bones
        StateUtility.RecoverState(savedState)

    @staticmethod
    def IKHierarchy (bonesListN,parentBoneN,bpy):


        childrenListN = []
        for b in bonesListN:
            childBone = bpy.context.object.data.edit_bones[b].children[0].name
            childrenListN.append(childBone)

        #parent children list to parentBoneN
        for b in childrenListN:
            
            aimBone = bpy.context.object.data.edit_bones[b]
            print("old parent "+ aimBone.parent.name)
            print(parentBoneN)
            try: 
                aimBone.parent = bpy.context.object.data.edit_bones[parentBoneN]
            except:
                print("can't parent")
            print("new parent "+ aimBone.parent.name)

        #force pose mode to return to original state
        bpy.ops.object.mode_set(mode='POSE')

        #adds ik constraint modifier to editBonesList
        for i in range(len(bonesListN)):
            ikBoneP = bpy.context.object.pose.bones[bonesListN[i]]
            ik = ikBoneP.constraints.new('IK')
            ik.target = bpy.context.object
            ik.subtarget = childrenListN[i]
            ik.chain_count = 1