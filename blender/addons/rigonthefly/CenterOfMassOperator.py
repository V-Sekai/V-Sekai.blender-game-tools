#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . CenterOfMass import CenterOfMassUtils

class CenterOfMassOperator(bpy.types.Operator):
    bl_idname = "view3d.center_of_mass_operator"
    bl_label = "Simple operator"
    bl_description = "adds an extra bone with it's location driven by selected bones. influence of each bone can be edited under the new bone's custom properties"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        CenterOfMassUtils.CenterOfMass(self, context)
        return {'FINISHED'}