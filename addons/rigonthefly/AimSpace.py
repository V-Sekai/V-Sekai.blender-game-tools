#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

class AimSpaceUtils:
    
    @staticmethod
    def RemoveEditableBone(boneToRemove):
        StateUtility.SetEditMode()
        armature = bpy.context.object.data
        for bone in armature.edit_bones:
            if bone.name == boneToRemove.name:
                armature.edit_bones.remove(bone)

    def ChangeToAimSpace (self, context):

        #force edit mode
        StateUtility.SetEditMode()

        selectedRigBonesListE = list(bpy.context.selected_editable_bones)
        selectedRigBonesListE.sort(key = lambda x:len(x.parent_recursive))
        selectedRigBoneNameList = list()
        for selectedBone in selectedRigBonesListE:
            selectedRigBoneNameList.append(selectedBone.name)
            print(selectedBone)
            print(selectedBone.name)

        
        bpy.ops.armature.duplicate()
       
        #add .rig suffix to duplicate bones now known as rig bones.
        for copiedBones in bpy.context.selected_editable_bones: 
            copiedBones.name = copiedBones.name.replace(".rig.001","Aim.rig")
 
        #armature set to pose mode
        bpy.ops.object.mode_set(mode='POSE')


        aimBonesListP = bpy.context.selected_pose_bones.copy()
        aimBonesListP.sort(key = lambda x:len(x.parent_recursive))
        ikBonesListP = aimBonesListP[:-1]
        ikSubtargetListP = aimBonesListP[1:]

        #unparent aim bones for world space translation
        StateUtility.SetEditMode()

        aimBonesListE = bpy.context.selected_editable_bones.copy()
        aimBonesListE.sort(key = lambda x:len(x.parent_recursive))
        aimBoneNameList = list()
        for aimBone in aimBonesListE:
            aimBoneNameList.append(aimBone.name)
            aimBone.parent = None

        bpy.ops.object.mode_set(mode='POSE')

        #change rig bones' display to circle, rotation mode to euler YZX and adds copy transform constraint to copy the base armature's animation.
        for rigBone in aimBonesListP:
            rigBone.custom_shape = bpy.data.objects["Square"]
            rigBone.rotation_mode = 'YZX'
            copyTransforms = rigBone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = bpy.context.object
            copyTransforms.subtarget = rigBone.name.replace("Aim.rig",".rig")

        #define animation's frame range for future baking.    
        actionStart = bpy.data.actions[0].frame_range.x
        actionEnd = bpy.data.actions[0].frame_range.y

        #bake rig bones animation so that they have the same animation as the base armature.
        bpy.ops.nla.bake(frame_start=actionStart, frame_end=actionEnd, only_selected=True, visual_keying=True, clear_constraints=True, use_current_action=True, bake_types={'POSE'})

        for i in range(len(ikBonesListP)):
            ikBones = ikBonesListP[i]
            
            ik = ikBones.constraints.new('IK')
            ik.target = bpy.context.object
            ik.subtarget = ikSubtargetListP[i].name
            ik.chain_count = 1   

        def AssignCopyTransformConstraint(aimBoneName):
            deformBoneName = aimBoneName.replace("Aim.rig","")
            print(deformBoneName)
            bpy.context.object.pose.bones[deformBoneName].constraints["Copy Transforms"].subtarget = aimBoneName

        for aimBone in aimBonesListP:
            AssignCopyTransformConstraint(aimBone.name)

        StateUtility.SetEditMode()

        print(len(aimBoneNameList))
        print(len(aimBonesListE) == len(selectedRigBonesListE))
        for i in range(len(selectedRigBoneNameList)):
            print(selectedRigBoneNameList[i])
            selectedBoneRig = bpy.context.object.data.edit_bones[selectedRigBoneNameList[i]]
            aimBone =  bpy.context.object.data.edit_bones[aimBoneNameList[i]]
            print(selectedBoneRig)
            rigBoneChildren = selectedBoneRig.children
            print(len(rigBoneChildren))
            print("index {} aim: {} selected: {}".format(i, aimBone.name, selectedBoneRig.name))
            for child in rigBoneChildren:
                print("child: {}".format(child.name))
                if child.name not in selectedRigBoneNameList:
                    print("child not in selection")
                    child.parent = aimBone
            
            AimSpaceUtils.RemoveEditableBone(selectedBoneRig)
        
        bpy.ops.object.mode_set(mode='POSE')
