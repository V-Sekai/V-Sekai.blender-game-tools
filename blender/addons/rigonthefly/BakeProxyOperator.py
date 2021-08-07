#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . BakeProxy import BakeProxyUtils

class BakeProxyOperator(bpy.types.Operator):
    bl_idname = "view3d.bake_proxy_operator"
    bl_label = "Simple operator"
    bl_description = "Bakes animation from active object to it's original proxy rig"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):        
        BakeProxyUtils.BakeProxy(self, context)
        return {'FINISHED'}