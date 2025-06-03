#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

from . import duplicateBone
from . import boneCollections
from . import importControllerShapes
from . import rotfBake
from . import removeConstraints
from . import bakeRig

def Proxy():

    proxyObjectList = []
    if len(bpy.context.selected_objects)<1:
        print("No Object Selected")
        return

    for obj in bpy.context.selected_objects:
        if obj.override_library:
            proxyObjectList.append(obj)

    bpy.ops.object.mode_set(mode='OBJECT')

    proxyObjectDictionary = dict()
    for proxyObject in proxyObjectList:
        proxyArmature = proxyObject.data
        proxyMatrix = proxyObject.matrix_world

        targetBoneDictionary = dict()

        #list visible bones to key
        appVersion = bpy.app.version
        if appVersion[0] == 4:
            for pbone in obj.pose.bones:
                bone = pbone.bone
                boneN = bone.name
                #check if bone is not hidden, skip pbone if hidden
                if pbone.bone.hide:
                    pass

                #check if at least one of pbone's collections are visible, skip pbone if none of it's collections are visible
                allBCollectionsHidden = True
                for bCollection in pbone.bone.collections:
                    if bCollection.is_visible:
                        allBCollectionsHidden = False
                        break
                if allBCollectionsHidden:
                    pass
                
                boneN = bone.name
                boneMatrix = bone.matrix_local #head position and roll in edit mode
                boneTail = bone.tail_local #tail position in edit mode
                #parent name
                if bone.parent == None:
                    boneParentN = ""
                else:
                    boneParentN = bone.parent.name
                
                targetBoneDictionary[boneN] = [boneMatrix, boneTail, boneParentN]

                boneCollections.AddBoneToCollections(bone, [boneCollections.RotFAnimationColName])
                
        elif appVersion[0] == 3:
            visibleLayers = list()
            for i, layer in enumerate(obj.data.layers):
                if layer:
                    visibleLayers.append(i)

            for bone in proxyObject.data.bones:

                #check if bone is in a visible layer
                pboneIsInVisibleLayer = False
                for i in visibleLayers:
                    if bone.layers[i]:
                        pboneIsInVisibleLayer = True

                if pboneIsInVisibleLayer and not bone.hide: #check if bone is visible

                    boneN = bone.name
                    boneMatrix = bone.matrix_local #head position and roll in edit mode
                    boneTail = bone.tail_local #tail position in edit mode
                    #parent name
                    if bone.parent == None:
                        boneParentN = ""
                    else:
                        boneParentN = bone.parent.name

                    targetBoneDictionary[boneN] = [boneMatrix, boneTail, boneParentN]

        proxyObjectDictionary[proxyObject.name] = targetBoneDictionary

        newArmature = bpy.data.armatures.new(proxyArmature.name + ".copy") #create new armature with the same name as tragetArmature but ends with ".copy"
        newObject = bpy.data.objects.new(proxyObject.name + ".copy", newArmature) #create new object ending with ".copy" containing new armature
        newObject.rotf_copy_of_proxy = proxyObject #points to the linked/library overriden armature object
        newObject.matrix_world = proxyMatrix
        bpy.context.collection.objects.link(bpy.data.objects[newObject.name]) #add newObject to collection so that it is visible in the scene #bpy.data.collections['Collection']
        bpy.context.view_layer.objects.active = bpy.data.objects[newObject.name] #set newObject to active

    bpy.ops.object.mode_set(mode='EDIT')

    for proxyObjectN in proxyObjectDictionary:
        for boneN, dataList in proxyObjectDictionary[proxyObjectN].items():
            boneMatrix = dataList[0] #head position and roll in edit mode
            boneTail = dataList[1]
            boneParentN = dataList[2]

            bone = newArmature.edit_bones.new(boneN)
            bone.matrix = boneMatrix #head position and roll
            bone.tail = boneTail #tail position

            newBoneParent = newArmature.edit_bones.get(boneParentN) #convert parent name to edit bone
            bone.parent = newBoneParent

    bpy.ops.object.mode_set(mode='POSE')

    for proxyObject in proxyObjectList:
        
        proxyObjectCopy = bpy.data.objects[proxyObject.name + ".copy"]
        proxyObjectCopy.animation_data_create() #add animation data to proxy object's copy
        if proxyObject.animation_data:
            if proxyObject.animation_data.action:
                proxyObjectCopy.animation_data.action = proxyObject.animation_data.action #have both the proxy object's copy use the same action as the proxy object

        appVersion = bpy.app.version
        if appVersion[0] == 4:
            pass
        elif appVersion[0] == 3:
            for boneGroup in proxyObject.pose.bone_groups: #create bone groups for the proxy object's copy
                boneGroupCopy = proxyObjectCopy.pose.bone_groups.new(name=boneGroup.name)
                boneGroupCopy.color_set = boneGroup.color_set

        for pboneCopy in proxyObjectCopy.pose.bones:
            boneN = pboneCopy.name #bone name is the same for both proxy object and it's copy
            pbone = proxyObject.pose.bones[boneN]

            appVersion = bpy.app.version
            if appVersion[0] == 4:
                pass
            elif appVersion[0] == 3:
                pboneCopy.bone_group_index = pbone.bone_group_index

            #assign controller shape to orient bone
            proxy_customShape = bpy.context.scene.rotf_proxy_customShape
            if proxy_customShape == None:
                importControllerShapes.ImportControllerShapes(["RotF_Circle"])
                pboneCopy.custom_shape = bpy.data.objects['RotF_Circle']
            else:
                pboneCopy.custom_shape = bpy.data.objects[proxy_customShape.name]

            #have the proxy bone follow the copy bone
            copyTransforms = pbone.constraints.new('COPY_TRANSFORMS')
            copyTransforms.name += " RotF"
            copyTransforms.target = proxyObjectCopy
            copyTransforms.subtarget = boneN

            pbone.bone.hide = True

def RemoveProxy():
    proxyObjList = list()
    copyObjList = list()
    for obj in bpy.context.selected_objects:
        proxyObj = obj.rotf_copy_of_proxy
        if proxyObj:
            proxyObjList.append(proxyObj)
            copyObjList.append(obj)

            if bpy.context.active_object == proxyObj or bpy.context.active_object.type != 'ARMATURE':
                bpy.context.view_layer.objects.active = obj

    #bake the copy armature motion
    bakeRig.BakeRig(copyObjList)

    for proxyObj, copyObj in zip(proxyObjList, copyObjList):

        #find in the copy armature the bones that share the same as the ones in the proxy armature
        proxyPBonesList= list()
        for bone in copyObj.data.bones:
            #bones that got copied from the proxy armature are not marked as rotf bones
            if bone.is_rotf != False:
                continue
            
            proxyPBone = proxyObj.pose.bones.get(bone.name)
            if not proxyPBone:
                continue
            
            #those bones should have been hidden from the process of making the copy armature when using the Proxy button
            proxyPBone.bone.hide = False
            proxyPBonesList.append(proxyPBone)

        removeConstraints.RemoveAllRotFConstraints(proxyPBonesList)

        #delete the copy armature that was created by Rig on the Fly
        bpy.data.objects.remove(copyObj)

        #add the proxy armature to the selection
        proxyObj.select_set(True)

        #if there are no active object, make the proxy object active so that we can set the mode to pose mode
        if not bpy.context.active_object:
            bpy.context.view_layer.objects.active = proxyObj

        bpy.ops.object.mode_set(mode='POSE')