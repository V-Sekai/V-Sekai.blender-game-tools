#########################################
#######       Rig On The Fly      #######
####### Copyright © 2022 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from ..core import dynamics

DYNAMICS_ID = '_ROTF_DYNAMICS'


class DynamicsOperator(bpy.types.Operator):
    bl_idname = "rotf.dynamics_on_transforms"
    bl_label = "Dynamics On Transforms"
    bl_description = "Adds dynamics to the desired transforms between the start and end frames using the different settings"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    transformsType : bpy.props.StringProperty()

    def execute(self, context):
        dynamics.Dynamics(self.transformsType, bpy.context.selected_pose_bones)
        return {'FINISHED'}