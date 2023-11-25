import bpy
from uvflow.addon_utils import Register, Property
from bpy.types import Context

def get_material_objects(context):
    material = context.active_object.active_material
    objects = []
    for obj in context.view_layer.objects:
        for slot in obj.material_slots:
            if slot.material == material:
                objects.append(obj)
                break
    return objects

@Register.OPS.GENERIC
class MaterialSelectObjects:
    label: str = 'Select Objects'
    bl_description = 'Select all objects that share the active material'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.object.type =='MESH'
    
    def action(self, context: Context):
        objects = get_material_objects(context)
        for obj in objects:
            obj.select_set(True)

@Register.OPS.GENERIC
class MaterialSelectFaces:
    label: str = 'Select Faces'
    bl_description = 'Select all faces that are assigned to the active material'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.object.type =='MESH'
    
    def action(self, context: Context):
        material = context.active_object.active_material
        objects = get_material_objects(context)
        bpy.ops.object.select_all(action='DESELECT')

        for obj in objects:
            obj.select_set(True)
            material_index = 0
            for slot in obj.material_slots:
                if slot.material == material:
                    material_index = slot.slot_index
                    break
            for poly in obj.data.polygons:
                if poly.material_index == material_index:
                    poly.select = True
                else:
                    poly.select = False
                    
        bpy.ops.object.mode_set(False, mode='EDIT')



