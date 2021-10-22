#########################################
#######       Rig On The Fly      #######
####### Copyright © 2020 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy
from . PolygonShapesUtility import PolygonShapes

class PolygonShapesUtilityOperator(bpy.types.Operator):
    bl_idname = "view3d.polygon_shapes_operator"
    bl_label = "Simple operator"
    bl_description = "Adds controller shapes to the blender file"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        PolygonShapes.AddControllerShapes()
        return {'FINISHED'}