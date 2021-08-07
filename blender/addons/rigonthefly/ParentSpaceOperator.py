#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . ParentSpaceUtility import ParentSpaceUtils
from . PolygonShapesUtility import PolygonShapes

class ParentSpaceOperator(bpy.types.Operator):
    bl_idname = "view3d.parent_space_operator"
    bl_label = "Simple operator"
    bl_description = "Parent selected controllers to the active controller"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        PolygonShapes.AddControllerShapes() #add conrtoller shapes to the scene
        
        result = ParentSpaceUtils.ParentSpaceCondition()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}

        selectionResult = ParentSpaceUtils.ParentSelectionCondition()
        if selectionResult != None:
            self.report(*selectionResult) # * unpacks list into a tuple
            return {'CANCELLED'}

        mainParentObjectBoneList = ParentSpaceUtils.ParentDuplicateRename()

        SortSelectionIntoDictionariesResults = ParentSpaceUtils.SortSelectionIntoDictionaries()

        activeObjectChildrenNList = SortSelectionIntoDictionariesResults[0]
        nonActiveObjectDictionary = SortSelectionIntoDictionariesResults[1]

        ParentSpaceUtils.ParentActiveArmature(activeObjectChildrenNList, mainParentObjectBoneList)

        ParentSpaceUtils.ParentNonActiveArmature(nonActiveObjectDictionary, mainParentObjectBoneList)

        #end with new parent bone selected
        bpy.context.object.data.bones[mainParentObjectBoneList[1]].select = True

        return {'FINISHED'}