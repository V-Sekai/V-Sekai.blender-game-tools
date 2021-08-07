#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . WorldPosition import WorldPositionUtils

class WorldPositionOperator(bpy.types.Operator):
    bl_idname = "view3d.world_position_operator"
    bl_label = "Simple operator"
    bl_description = "Changes selected controllers tranforms to world space"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        WorldPositionUtils.WorldPosition(self, context)
        return {'FINISHED'}