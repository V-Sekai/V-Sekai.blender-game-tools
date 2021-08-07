#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . GroupSection import GroupSectionUtils

class GroupSectionOperator(bpy.types.Operator):
    bl_idname = "view3d.group_section_operator"
    bl_label = "Simple operator"
    bl_description = "groups selected chain of bones under a new bone"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        GroupSectionUtils.GroupSection(self, context)
        return {'FINISHED'}