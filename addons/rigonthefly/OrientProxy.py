#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility, Channel
from . PolygonShapesUtility import PolygonShapes
from . DypsloomBake import DypsloomBakeUtils
from . AutoBoneOrient import AutoBoneOrientUtils

class OrientProxyUtils:
    def OrientProxy (self, context):
        currentFrame = bpy.context.scene.frame_current #set aside current frame to come back to it at the end of the script

        bpy.context.scene.frame_set(0) #set current frame to 0

        PolygonShapes.AddControllerShapes() #add controller shapes to the scene

        targetObject = bpy.context.active_object # proxy rig object to copy

        targetBoneDictionary = OrientProxyUtils.DuplicateProxyRig(targetObject)
        targetObject.hide_set(True)#hide proxy rig object

        #make target proxy rig bones' follow the new rig 
        for boneN in targetBoneDictionary:
            boneP = targetObject.pose.bones[boneN]
            copyTransforms = boneP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = bpy.context.active_object
            copyTransforms.subtarget = StateUtility.LeftRightSuffix(boneN) + ".proxy.child"

        bpy.context.scene.frame_current = currentFrame #return to initial frame

    @staticmethod
    def DuplicateProxyRig(targetObject):
        targetArmature = targetObject.data
        targetMatrix = targetObject.matrix_world

        baseLayer = targetObject.baseBonesLayer
        rigLayer = targetObject.rigBonesLayer

        translatorLayer = targetObject.translatorBonesLayer
        

        orientChildNList = list()
        orientBonesNList = list()
        orientRigNList = list()

        #StateUtility.SetEditMode
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')

        targetBoneDictionary = dict() #to contain the bones info from the target proxy rig needed create a copy of it that is not linked/referenced

        selectedPoseBones = bpy.context.selected_pose_bones.copy()
        selectedPoseBones.sort(key = lambda x:len(x.parent_recursive))

        #add bone info to copy to targetBoneDictionary
        for boneP in selectedPoseBones:
            bone = boneP.bone
            boneN = bone.name
            boneMatrix = bone.matrix_local #head position and roll in edit mode
            boneTail = bone.tail_local #tail position in edit mode
            #parent name
            if bone.parent == None:
                boneParentN = ""
            else:
                boneParentN = bone.parent.name

            targetBoneDictionary[boneN] = [boneMatrix, boneTail, boneParentN]
        
        bpy.ops.pose.select_all(action='DESELECT')

        bpy.ops.object.mode_set(mode='OBJECT')
        #deselect all
        bpy.ops.object.select_all(action='DESELECT')

        newArmature = bpy.data.armatures.new(targetArmature.name + ".copy") #create new armature with the same name as tragetArmature but ends with ".copy"
        newObject = bpy.data.objects.new(targetObject.name + ".copy", newArmature) #create new object ending with ".copy" containing new armature
        newObject.matrix_world = targetMatrix
        bpy.context.collection.objects.link(bpy.data.objects[newObject.name]) #add newObject to collection so that it is visible in the scene #bpy.data.collections['Collection']
        bpy.context.view_layer.objects.active = bpy.data.objects[newObject.name] #set newObject to active

        #set to edit mode
        bpy.ops.object.mode_set(mode='EDIT')

        #create new bones
        for boneN in targetBoneDictionary:
            newBoneN = StateUtility.LeftRightSuffix(boneN) + ".proxy.child"
            newBone = newArmature.edit_bones.new(newBoneN) #boneN + ".proxy.rig")
            newBone.matrix = targetBoneDictionary[boneN][0] #head position and roll
            newBone.tail = targetBoneDictionary[boneN][1] #tail position
            boneParentN = targetBoneDictionary[boneN][2]
            newboneParentN = StateUtility.LeftRightSuffix(boneParentN) + ".proxy.child" #parent name

            newBoneParent = newArmature.edit_bones.get(newboneParentN) #convert parent name to edit bone
            newBone.parent = newBoneParent #set a newBoneParent as parent of boneN

            newBone.use_deform = False

            orientChildNList.append(newBoneN)
            """
            #move bone to base layer
            newBone.layers[translatorLayer]=True
            newBone.layers[0]=False
            """
        #show layer 2 and hide layer 1 of the armature
        newArmature.layers[baseLayer]=True
        newArmature.layers[rigLayer]=True
        newArmature.layers[translatorLayer]=True

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #add pose bones groups to the newAmrature
        if newObject.pose.bone_groups.get('RigOnTheFly Base') is None:
            baseBoneGroup = newObject.pose.bone_groups.new(name="RigOnTheFly Base")
            baseBoneGroup.color_set = 'THEME09'

        if newObject.pose.bone_groups.get('RigOnTheFly Right') is None:
            rightBoneGroup = newObject.pose.bone_groups.new(name="RigOnTheFly Right")
            rightBoneGroup.color_set = 'THEME01'

        if newObject.pose.bone_groups.get('RigOnTheFly Left') is None:
            leftBoneGroup = newObject.pose.bone_groups.new(name="RigOnTheFly Left")
            leftBoneGroup.color_set = 'THEME04'

        leftSide = ["left","_l","l_",".l","l.","-l","l-"," left","left "]
        rightSide = ["right","_r","r_",".r","r.","-r","r-"," right","right "]

        newObject.baseBonesLayer = targetObject.baseBonesLayer
        newObject.rigBonesLayer = targetObject.rigBonesLayer
        newObject.unusedRigBonesLayer = targetObject.unusedRigBonesLayer
        newObject.notOrientedBonesLayer = targetObject.notOrientedBonesLayer
        newObject.translatorBonesLayer = targetObject.translatorBonesLayer

        for i, boneN in enumerate(targetBoneDictionary): #newObject.pose.bones):
            rigBN = StateUtility.LeftRightSuffix(boneN) +".proxy.child"
            boneP = newObject.pose.bones[rigBN]
            #boneP.custom_shape = bpy.data.objects["RotF_Circle"]
            bpy.context.object.data.bones[boneP.name].show_wire = True
            #boneP.rotation_mode = 'YZX'

            #for the first two bones of the hierarchy have the controller size bigger
            if i < 2:
                objDimensions = (newObject.dimensions[0] + newObject.dimensions[1] + newObject.dimensions[2])/3
                objWorldScaleV = newObject.matrix_world.to_scale()
                objWorldScale = (objWorldScaleV[0] + objWorldScaleV[1] + objWorldScaleV[2])/3
                objSize = objDimensions / objWorldScale
                sizeMultiplyer = objSize / boneP.length
                boneP.custom_shape_scale *= sizeMultiplyer/(2*(i+3))

            boneOriginalName = boneN #boneP.name.replace(".proxy.rig","")

            if any(boneOriginalName.casefold().startswith(left) or boneOriginalName.casefold().endswith(left) for left in leftSide):
                boneP.bone_group = leftBoneGroup
            elif any(boneOriginalName.casefold().startswith(right) or boneOriginalName.casefold().endswith(right) for right in rightSide):
                boneP.bone_group = rightBoneGroup
            else:
                boneP.bone_group = baseBoneGroup

            boneP.bone.select = True
        #set to edit mode
        StateUtility.SetEditMode()

        StateUtility.MoveBonesToLayer(translatorLayer)

        #duplicate .orient. Duplicated bones are selected from this operation
        bpy.ops.armature.duplicate()

        orientBonesNList = list()

        for ebone in bpy.context.selected_bones:
            ebone.name = ebone.name.replace(".child.001", ".orient")
            orientBonesNList.append(ebone.name)

        StateUtility.MoveBonesToLayer(baseLayer)
        
        #orient the dupliacted bones to work better with Blender's constraints
        AutoBoneOrientUtils.OrientBones(newArmature, orientBonesNList)

        #MAKE ORIENT BONES MIRROR
        newObject.data.use_mirror_x = True
        
        for ebone in bpy.context.selected_editable_bones:
            if "R." in ebone.name:
                ebone.roll = ebone.roll
        
        #duplicate .orient. Duplicated bones are selected from this operation
        bpy.ops.armature.duplicate()
        
        for ebone in bpy.context.selected_bones:
            ebone.name = ebone.name.replace(".orient.001", ".orient.rig")
            orientRigNList.append(ebone.name)
        StateUtility.MoveBonesToLayer(rigLayer)

        for orientChildN in orientChildNList:
            orientChildE = newArmature.edit_bones[orientChildN]
            orientBoneN = orientChildN.replace(".child",".orient")
            orientChildE.parent = newArmature.edit_bones[orientBoneN]

        #StateUtility.SetEditMode
        bpy.ops.object.mode_set(mode='POSE')

        for orientBoneN in orientBonesNList:
            orientBoneP = newObject.pose.bones[orientBoneN]
            copyTransforms = orientBoneP.constraints.new('COPY_TRANSFORMS')
            copyTransforms.target = newObject
            copyTransforms.subtarget = orientBoneN + ".rig"
        
        for orientRigN in orientRigNList:
            orientRigP = newObject.pose.bones[orientRigN]
            orientRigP.custom_shape = bpy.data.objects["RotF_Circle"]
            #bpy.context.object.data.bones[orientRigN].show_wire = True

        #show layer 2 and hide layer 1 of the armature
        newArmature.layers[baseLayer]=False
        newArmature.layers[translatorLayer]=False
        newArmature.layers[0]=False

        return targetBoneDictionary


