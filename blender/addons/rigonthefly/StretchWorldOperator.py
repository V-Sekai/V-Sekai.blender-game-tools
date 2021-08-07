#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . StretchWorld import StretchWorldUtils

class StretchWorldOperator(bpy.types.Operator):
    bl_idname = "view3d.stretch_world_operator"
    bl_label = "Simple operator"
    bl_description = "Changes rig selected bones to stretch world"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        StretchWorldUtils.ChangeToStretchWorld(self, context)
        return {'FINISHED'}
