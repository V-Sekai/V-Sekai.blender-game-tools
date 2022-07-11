import bpy
from ..core import baseControllerShape
from ..core import proxy
from ..core import orient
from ..core import extraBone
from ..core import rootMotion

ARMATURETOOLS_ID = '_ROTF_ARMATURETOOLS'

class BaseControllerShapeOperator(bpy.types.Operator):
    bl_idname = "rotf.base_controller_shape"
    bl_label = "Base Controller Shape"
    bl_description = "Adds a controller shape to all bones not using one in the visible layers and assign them a left middle and right bone group"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        baseControllerShape.BaseControllerShape()
        return {'FINISHED'}

class ProxyOperator(bpy.types.Operator):
    bl_idname = "rotf.proxy"
    bl_label = "Proxy"
    bl_description = "Duplicates the seleceted proxy armatures"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = proxy.Proxy()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}

class OrientOperator(bpy.types.Operator):
    bl_idname = "rotf.orient"
    bl_label = "Orient"
    bl_description = "Creates basic FK rig on skeleton. Fixing orientation issues. Ideal for rigs coming from other 3D softwares"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = orient.Orient()
        if result != None:
            self.report(*result) # * unpacks list into a tuple
            return {'CANCELLED'}
        return {'FINISHED'}

class AddBoneOperator(bpy.types.Operator):
    bl_idname = "rotf.add_bone"
    bl_label = "Add Bone"
    bl_description = "Add an extra bone aligned to the world scene"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = extraBone.AddBone()
        return {'FINISHED'}

class RootMotionOperator(bpy.types.Operator):
    bl_idname = "rotf.root_motion"
    bl_label = "Root Motion"
    bl_description = "Adds a bone at the base of the hierarchy and transfer the object's motion onto it"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = rootMotion.RootMotion()
        return {'FINISHED'}

class RemoveRootMotionOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_root_motion"
    bl_label = "Remove"
    bl_description = "Transfers the selected Root bones motion onto their respective objects before removing them"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = rootMotion.RemoveRootMotion()
        return {'FINISHED'}

class CenterOfMassOperator(bpy.types.Operator):
    bl_idname = "rotf.center_of_mass"
    bl_label = "Center of Mass"
    bl_description = "Creates a controller with it's location driven between the selected bones"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = extraBone.CenterOfMass()
        return {'FINISHED'}

class RemoveCenterOfMassOperator(bpy.types.Operator):
    bl_idname = "rotf.remove_center_of_mass"
    bl_label = "Remove Center of Mass"
    bl_description = "Removes selected center of mass controllers"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        result = extraBone.RemoveCenterOfMass()
        return {'FINISHED'}
