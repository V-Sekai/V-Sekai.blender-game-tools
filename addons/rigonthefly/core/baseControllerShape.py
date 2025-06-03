#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . import boneCollections
from . import importControllerShapes

leftSide = ["left","_l","l_",".l","l.","-l","l-"," left","left "]
rightSide = ["right","_r","r_",".r","r.","-r","r-"," right","right "]

def BaseControllerShape():
    #set to pose mode
    bpy.ops.object.mode_set(mode='POSE')

    obj = bpy.context.object
    
    appVersion = bpy.app.version #returns the app version in list form, eg. (4,0,0)

    #for obj in bpy.context.selected_objects:
        #if obj.type == 'ARMATURE':
    obj.show_in_front = True

    if appVersion[0] == 3:
        #add RigOnTheFly pose bone's groups if they do not exist yet
        pboneGroups = obj.pose.bone_groups
        
        baseBoneGroup = pboneGroups.get('RigOnTheFly Middle')
        if baseBoneGroup is None:
            baseBoneGroup = pboneGroups.new(name="RigOnTheFly Middle")
            baseBoneGroup.color_set = 'THEME09'

        rightBoneGroup = pboneGroups.get('RigOnTheFly Right')
        if rightBoneGroup is None:
            rightBoneGroup = pboneGroups.new(name="RigOnTheFly Right")
            rightBoneGroup.color_set = 'THEME01'

        leftBoneGroup = pboneGroups.get('RigOnTheFly Left')
        if leftBoneGroup is None:
            leftBoneGroup = pboneGroups.new(name="RigOnTheFly Left")
            leftBoneGroup.color_set = 'THEME04'

        extraBoneGroup = pboneGroups.get('RigOnTheFly Extra')
        if extraBoneGroup is None:
            extraBoneGroup = pboneGroups.new(name="RigOnTheFly Extra")
            extraBoneGroup.color_set = 'THEME03'

        #list object's visible layers
        visibleLayers = list()
        for i, layer in enumerate(obj.data.layers):
            if layer:
                visibleLayers.append(i)

        for pbone in obj.pose.bones:
            #check if bone is in a visible layer
            pboneIsInVisibleLayer = False
            for i in visibleLayers:
                if pbone.bone.layers[i]:
                    pboneIsInVisibleLayer = True
                    break

            if pboneIsInVisibleLayer:
                #assign bone groups if they do not already use one
                if pbone.bone_group == None:
                    if any(pbone.name.casefold().startswith(left) or pbone.name.casefold().endswith(left) for left in leftSide):
                        pbone.bone_group = leftBoneGroup
                    elif any(pbone.name.casefold().startswith(right) or pbone.name.casefold().endswith(right) for right in rightSide):
                        pbone.bone_group = rightBoneGroup
                    #elif "RotF_ArmatureMotion" in pbone.name:
                    #    continue
                    else:
                        pbone.bone_group = baseBoneGroup

                #adds controller shapes if not already using one
                if pbone.custom_shape == None:
                    customShape = bpy.context.scene.rotf_base_customShape
                    if customShape == None:
                        importControllerShapes.ImportControllerShapes(["RotF_Circle"])
                        pbone.custom_shape = bpy.data.objects['RotF_Circle']
                    else:
                        pbone.custom_shape = bpy.data.objects[customShape.name]
    
    elif appVersion[0] == 4:
        armature = obj.data

        boneCollections.AddBaseBoneCollections(armature)

        for pbone in obj.pose.bones:
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

            #change bone's color if it's using the default palette
            if pbone.bone.color.palette == 'DEFAULT':

                if any(pbone.name.casefold().startswith(left) or pbone.name.casefold().endswith(left) for left in leftSide):
                    pbone.bone.color.palette = 'THEME04'

                elif any(pbone.name.casefold().startswith(right) or pbone.name.casefold().endswith(right) for right in rightSide):
                    pbone.bone.color.palette = 'THEME01'
                
                else:
                    pbone.bone.color.palette = 'THEME09'

            #adds controller shapes if not already using one
            if pbone.custom_shape == None:
                customShape = bpy.context.scene.rotf_base_customShape
                if customShape == None:
                    importControllerShapes.ImportControllerShapes(["RotF_Circle"])
                    pbone.custom_shape = bpy.data.objects['RotF_Circle']
                else:
                    pbone.custom_shape = bpy.data.objects[customShape.name]



