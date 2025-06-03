#########################################
#######       Rig On The Fly      #######
####### Copyright © 2024 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

class UnhideAllBonesOperator(bpy.types.Operator):
    bl_idname = "rotf.unhide_all_bones"
    bl_label = "Unhide All Bones"
    bl_description = "Unhide all bones of the active armature."
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        obj = bpy.context.active_object
        if obj and obj.type == 'ARMATURE':
            armature = obj.data

            for bone in armature.bones:
                bone.hide = False
        return {'FINISHED'}
    
class ShowROTFCollectionOperator(bpy.types.Operator):
    bl_idname = "rotf.show_rotf_collection"
    bl_label = "Show RotF Bone Collection"
    bl_description = "Shows bones included in the corresponding RotF bone collection"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    collectionName : bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.context.active_object
        if obj and obj.type == 'ARMATURE':
            armature = obj.data

            collection = armature.collections[self.collectionName]
            for bone in collection.bones:
                bone.hide = False

            collection.is_visible = True

        return {'FINISHED'}
    
class HideROTFCollectionOperator(bpy.types.Operator):
    bl_idname = "rotf.hide_rotf_collection"
    bl_label = "Hide RotF Bone Collection"
    bl_description = "Hides bones included in the corresponding RotF bone collection"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    collectionName : bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.context.active_object
        if obj and obj.type == 'ARMATURE':
            armature = obj.data

            collection = armature.collections[self.collectionName]
            for bone in collection.bones:
                bone.hide = True

            collection.is_visible = False

        return {'FINISHED'}
    