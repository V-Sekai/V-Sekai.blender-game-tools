#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . Utility import StateUtility
from . PolygonShapesUtility import PolygonShapes

class CenterOfMassUtils:
    def CenterOfMass(self, context):

        pboneList = CenterOfMassUtils.ListToConstraintTo()
        #deselect all pose bones
        bpy.ops.pose.select_all(action='DESELECT')
        CoMpbone = CenterOfMassUtils.AddCoMBone()
        obj = CoMpbone.id_data

        #find scale offset to apply to the driver's expression
        scaleVector = obj.matrix_world.to_scale()
        scaleAverage = (scaleVector[0]+scaleVector[1]+scaleVector[2])/3
        scaleOffset = str(int(1/scaleAverage))

        #add custom property to parentBoneP to help point at .copy.parent.rig bones on other armatures when removing parent space
        rna_ui = CoMpbone.get('_RNA_UI')
        if rna_ui is None:
            CoMpbone['_RNA_UI'] = {}
            rna_ui = CoMpbone['_RNA_UI']
        
        for i in range(len(pboneList)): #use bones in pboneList to prepare the expresion that will drive CoM bone's location axis
            if i==0 :
                topVar = "("+"l" + str(i) + "*" + "w" + str(i)+ ") "
                totalWeightVar = "w" + str(i)
            else :
                topVar += "+("+ "l" + str(i) + "*" + "w" + str(i) + ") "
                totalWeightVar += "+w" + str(i)

        for i, pbone in enumerate(pboneList):
            nbone = pbone.name
            weightN = nbone + " Weight"
            #for each bone in pbone list, add to CoM bone a custom float property that goes from 0.001 to 100            
            CoMpbone[weightN] = float(100)
            CoMpbone["_RNA_UI"].update({weightN: {"min":0.001, "max":100.0, "soft_min":0.0, "soft_max":100.0}})

            #for each location axis of CoM bone, add a driver
            for locIndex in range(3):
                transformType = str()
                if locIndex == 0:
                    transformType = 'LOC_X'
                if locIndex == 1:
                    transformType = 'LOC_Y'
                if locIndex == 2:
                    transformType = 'LOC_Z'

                driver = obj.driver_add('pose.bones["' + CoMpbone.name +'"].location',locIndex).driver #add driver to one of CoM location axis

                #location variable of pbone in world space
                locVar = driver.variables.new()
                locVar.type = 'TRANSFORMS'
                locVar.name = "l" + str(i)
                locVar.targets[0].id = obj
                locVar.targets[0].bone_target = pbone.name
                locVar.targets[0].transform_type = transformType

                #weight variable from CoM bone's custom property
                weightVar = driver.variables.new()
                weightVar.name = "w" + str(i)
                weightVar.targets[0].id = obj
                weightVar.targets[0].data_path = 'pose.bones["' + CoMpbone.name +'"]["'+ weightN +'"]'

                driver.expression = scaleOffset +"*(" + topVar + ")/(" + totalWeightVar + ")" #assign expression using topVar and totalWeightVar prepared earlier

    @staticmethod
    def ListToConstraintTo():
        pboneList = list()

        suffixToDelete = ["IK","parent", "child", "world", "top", "rig", "parentCopy", "aimOffset"] #possible suffixes for bone name extensions
        tempBoneN = str() #to help find the version of the bones not containing the words from suffixToDelete

        for pbone in bpy.context.selected_pose_bones:

            if ".rig" in pbone.name: #if bone is a controller from RigOnTheFly
                obj = pbone.id_data
                selectedBoneN = pbone.name
                boneN = str()
                boneNSplit = selectedBoneN.split(".")

                #loop over each word split by '.' in the bone name
                previousMatch = False
                first = True
                for word in boneNSplit:
                    match = False
                    #check if one of the suffixes matches the word 
                    for suffix in suffixToDelete:
                        if word == suffix:
                            match = True

                    #if match remember word in case next word does not match 
                    if match:
                        tempBoneN = tempBoneN + "."+ word
                        previousMatch = True
                    else:

                        #if previous was a match use the temp words that was cached 
                        if previousMatch:
                            boneN = boneN + tempBoneN
                            previousMatch = False
                            tempBoneN = str()
                        
                        #the firt word does not start with a '.' but the others do
                        if first:
                            boneN = boneN + word
                        else:
                            boneN = boneN +"."+ word
                    first = False
                    
                boneN = boneN + ".rig"
                pbone = obj.pose.bones[boneN]
            
            pboneList.append(pbone)
        return pboneList

    @staticmethod
    def AddCoMBone():

        #add controller shapes to the scene
        PolygonShapes.AddControllerShapes()

        #force edit mode
        StateUtility.SetEditMode()

        obj = bpy.context.object
        armature = obj.data

        newBoneN = CenterOfMassUtils.ExtraBoneName(1)

        newBoneE = armature.edit_bones.new(newBoneN)
        newBoneE.use_deform = False
        newBoneE.tail = (0,0,1) #tail position

        #find the matrix coordinates of the armature object
        objectMatrix = obj.matrix_world
        #invert armature's matrix to find where global(0,0,0) is in relation to the armature's position/roation
        objectMatrixInvert= objectMatrix.copy()
        objectMatrixInvert.invert()
        #set aim bone position to global (0,0,0) with axis following world's
        newBoneE.matrix = objectMatrixInvert

        #force pose mode
        bpy.ops.object.mode_set(mode='POSE')

        #select new extra bone to change it's custom shape and viewport display
        armature.bones[newBoneN].select = True
        newBoneP = obj.pose.bones[newBoneN]
        newBoneP.custom_shape = bpy.data.objects["RotF_Locator"]
        newBoneE.show_wire=True

        #add pose bone's groups
        if obj.pose.bone_groups.get('RigOnTheFly Base') is None:
            baseBoneGroup = obj.pose.bone_groups.new(name="RigOnTheFly Base")
            baseBoneGroup.color_set = 'THEME09'
            newBoneP.bone_group = baseBoneGroup
        else:
            #set bone group of new extra bone to Base layer
            newBoneP.bone_group = obj.pose.bone_groups['RigOnTheFly Base']

        return newBoneP

    @staticmethod
    def ExtraBoneName (count):
        boneName = "CoM"+str(count)+".rig"

        if bpy.context.object.data.bones.get(boneName)==None:
            return boneName
        else:
            return CenterOfMassUtils.ExtraBoneName(count+1)
