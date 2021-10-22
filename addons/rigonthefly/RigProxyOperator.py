#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . RigProxy import RigProxyUtils
from . OrientProxy import OrientProxyUtils
from . RigOnSkeleton import RigOnSkeletonUtils

class RigProxyOperator(bpy.types.Operator):
    bl_idname = "view3d.rig_proxy_operator"
    bl_label = "Simple operator"
    bl_description = "Creates a control rig on proxy rig"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = bpy.context.scene
        if scene.orientRig:
            OrientProxyUtils.OrientProxy(self, context)
        else:
            RigProxyUtils.RigProxy(self, context)
        
        #RigOnSkeletonUtils.RestPoseTrack(self, context) #add a rest pose nla track
        return {'FINISHED'}