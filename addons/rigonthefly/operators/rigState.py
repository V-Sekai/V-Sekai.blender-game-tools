import bpy
import os

from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import StringProperty
from ..core import rigState
from ..core import bakeRig


class SaveRigStateOperator(bpy.types.Operator, ExportHelper):
    bl_idname = 'rotf.save_rig_state'
    bl_label = 'Save Rig State'
    bl_description = "Save the current rig state of the active armature"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    #bl_options = {'PRESET', 'UNDO'}

    filename_ext = '.rs'
    
    filter_glob: StringProperty(
        default='*.rs',
        options={'HIDDEN'}
    )

    def execute(self, context):
        file_name = rigState.SaveRigState(self.filepath)

        if not file_name:
            self.report({'ERROR'}, 'You don\'t have any custom naming schemes!')
            return {'FINISHED'}

        self.report({'INFO'}, 'Exported custom naming schemes as "' + file_name + '".')

        return {'FINISHED'}

class LoadFilePathOperator(bpy.types.Operator, ImportHelper):
    bl_idname = 'rotf.load_file_path'
    bl_label = 'Load File Path'
    bl_description = "Load folder path where rig states are located"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    filter_glob: StringProperty(
        default='*.rs',
        options={'HIDDEN'}
    )


    def execute(self, context):
        
        filePath = self.filepath

        folderPath = os.path.dirname(filePath)
        folderName = os.path.basename(folderPath)

        scene =bpy.context.scene
        scene.rotf_folder_name = folderName
        scene.rotf_folder_path = folderPath
        
        scene.rotf_state_collection.clear()
        for file in os.listdir(folderPath):
            if file.endswith(".rs"):
                newFile = scene.rotf_state_collection.add()
                newFile.filename = os.path.basename(file)[:-3] #remove ".rs" from file name
                #newFile.filepath = file

        if not filePath:
            self.report({'ERROR'}, 'You don\'t have any custom naming schemes!')
            return {'FINISHED'}

        self.report({'INFO'}, 'Exported custom naming schemes as "' + filePath + '".')

        return {'FINISHED'}

class LoadRigStateOperator(bpy.types.Operator):
    bl_idname = 'rotf.load_rig_state'
    bl_label = 'Load Rig State'
    bl_description = "Load a rig state onto the active armature"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    #bl_options = {'PRESET', 'UNDO'}

    filename : bpy.props.StringProperty()

    def execute(self, context):
        scene = bpy.context.scene
        
        if scene.rotf_bake_on_load:
            print("baking rig before loading rig state")
            objectList = [bpy.context.active_object]
            #bake all the rig
            bakeRig.BakeRig(objectList)
        
        filepath = os.path.join(scene.rotf_folder_path, self.filename + ".rs")

        result = rigState.LoadRigState(filepath)
        
        if result['Success'] == False:
            warning = ", ".join(result['Result'])
            self.report(*[{'WARNING'}, warning]) # * unpacks list into a tuple
        else:
            self.report({'INFO'}, 'Rig State "'+self.filename+'" Loaded Successfully')

        return {'FINISHED'}

class BakeRigOperator(bpy.types.Operator):
    bl_idname = "rotf.bake_rig"
    bl_label = "Bake Rig"
    bl_description = "Bakes the rig, removing all RotF controllers and constraints"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        
        selectedArmatureObjects = list()
        for obj in bpy.context.selected_objects:
            if obj.type =='ARMATURE':
                selectedArmatureObjects.append(obj)
        bakeRig.BakeRig(selectedArmatureObjects)
        return {'FINISHED'}