#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

from . import duplicateBone
from . import importControllerShapes
from . import rotfBake

def Proxy():
    print("Duplicating proxy")

    proxyObjectList = []
    if len(bpy.context.selected_objects)<1:
        print("No Object Selected")
        return

    for obj in bpy.context.selected_objects:
        if obj.proxy or obj.override_library:
            proxyObjectList.append(obj)

    bpy.ops.object.mode_set(mode='OBJECT')

    proxyObjectDictionary = dict()
    for proxyObject in proxyObjectList:
        proxyArmature = proxyObject.data
        proxyMatrix = proxyObject.matrix_world

        targetBoneDictionary = dict()

        #list visible bones to key
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
        proxyObjectCopy.animation_data.action = proxyObject.animation_data.action #have both the proxy object's copy use the same action as the proxy object

        for boneGroup in proxyObject.pose.bone_groups: #create bone groups for the proxy object's copy
            boneGroupCopy = proxyObjectCopy.pose.bone_groups.new(name=boneGroup.name)
            boneGroupCopy.color_set = boneGroup.color_set

        for pboneCopy in proxyObjectCopy.pose.bones:
            boneN = pboneCopy.name #bone name is the same for both proxy object and it's copy
            pbone = proxyObject.pose.bones[boneN]

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