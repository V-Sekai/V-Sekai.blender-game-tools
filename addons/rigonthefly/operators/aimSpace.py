import bpy
from ..core import aimSpace
from ..core import aimOffsetSpace

AIMSPACE_ID = '_ROTF_AIMSPACE'


class AimSpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.aim_space"
    bl_label = "Aim Space"
    bl_description = "Changes selected controllers to aim space"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = aimSpace.AimSpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}

class AimOffsetSpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.aim_offset_space"
    bl_label = "Aim Offset Space"
    bl_description = "Changes selected controllers to aim space pointing at the 3D cursor's position"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = aimOffsetSpace.AimOffsetSpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}

class RemoveAimSpaceOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_aim_space"
    bl_label = "Remove Aim Space"
    bl_description = "Changes selected Aim space controllers back to their original space"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = aimSpace.RemoveAimSpace()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}