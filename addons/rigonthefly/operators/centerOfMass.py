import bpy
from ..core import centerOfMass

CENTEROFMASS_ID = '_ROTF_CENTEROFMASS'

class CenterOfMassOperator(bpy.types.Operator):
    bl_idname = "rotf.center_of_mass"
    bl_label = "Center of Mass"
    bl_description = "Creates a controller with it's location driven between the selected bones"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = centerOfMass.CenterOfMass()
        return {'FINISHED'}
    
class AddToCenterOfMassOperator(bpy.types.Operator):
    bl_idname = "rotf.add_to_center_of_mass"
    bl_label = "Add to Center of Mass"
    bl_description = "Adds selected controllers to the active center of mass' list of influence"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = centerOfMass.AddToCenterOfMass()
        return {'FINISHED'}
    
class RemoveFromCenterOfMassOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_from_center_of_mass"
    bl_label = "Remove from Center of Mass"
    bl_description = "Removes selected bones from affecting the active center of mass bone"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = centerOfMass.RemoveFromCenterOfMass()
        return {'FINISHED'}

class RemoveCenterOfMassOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_center_of_mass"
    bl_label = "Remove Center of Mass"
    bl_description = "Removes selected center of mass controllers"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = centerOfMass.RemoveCenterOfMass()
        return {'FINISHED'}