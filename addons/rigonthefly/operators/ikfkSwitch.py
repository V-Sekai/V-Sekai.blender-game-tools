#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from ..core import ikLimb, ikStretch, fkLimb

FKIKSWITCH_ID = '_ROTF_IKFKSWITCH'


class IKLimbOperator(bpy.types.Operator):
    bl_idname = "rotf.ik_limb"
    bl_label = "IK Limb"
    bl_description = "Changes selected controllers to work in IK."
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = ikLimb.IKLimb()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}
    
class FKLimbOperator(bpy.types.Operator):
    bl_idname = "rotf.fk_limb"
    bl_label = "FK Limb"
    bl_description = "Changes selected IK handle controller back to working in FK"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        fkLimb.FKLimb()
        return {'FINISHED'}
    
class IKStretchOperator(bpy.types.Operator):
    bl_idname = "rotf.ik_stretch"
    bl_label = "IK Stretch"
    bl_description = "Changes selected controllers to work in IK."
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = ikStretch.IKStretch()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}
    
class RemoveIKStretchOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_ik_stretch"
    bl_label = "Remove IK Stretch"
    bl_description = "Changes selected IK Stretch bones back to FK."
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = ikStretch.RemoveIKStretchSpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}