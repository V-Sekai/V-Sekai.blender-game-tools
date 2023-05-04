bl_info = {
    "name": "QOL RingArray",
    "author": "Rico Holmes",
    "version": (1, 0, 5),
    "blender": (3, 3, 0),
    "location": "View3D",
    "description": "Create a quick ring array from selected object",
    "warning": "",
    "wiki_url": "",
    "category": "Interface",
    }

import bpy,math
from bpy.props import *
from copy import copy as copy
from .prefs import *
from .functions import *
from bpy.types import (Operator,Panel) 


class QOL_RingArray(Operator):
    """Make a circular array of things"""
    bl_idname = "wm.qol_ringarray"
    bl_label = "QOL RingArray"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Make a circular array of things"
    bl_space_type = 'VIEW_3D'
    
    #add properties
    number_of_objects : IntProperty(name="Number of objects",default=6,min=1,max=1000)
    radius_of_circle : FloatProperty(name="Radius of circle",default=.2,min=0.0001)
    offset_angle : FloatProperty(name="Offset angle",default=0)
    apply_transform : BoolProperty(name="Apply transform",default=True)
    hub_axis : EnumProperty(name="Axis",items=[ ('X', "X", "X"),('Y', "Y", "Y"),('Z', "Z", "Z")],default = "Z",)
    delete_original : BoolProperty(name="Delete original",default=False)
    linked_data : BoolProperty(name="Linked data",default=True)
    create_parent : BoolProperty(name="Create parent",default=False)
    merge_objects : BoolProperty(name="Merge objects",default=False)
    autoAxis : BoolProperty(name="Auto axis",default=True)
    resize : FloatProperty(name="Resize",default=1,min=0.0001,max=10000)
    tx: FloatProperty(name="tx",default=0)
    ty: FloatProperty(name="ty",default=0)
    tz: FloatProperty(name="tz",default=0)
    ry: FloatProperty(name="ry",default=0)
    rx: FloatProperty(name="rx",default=0)
    rz: FloatProperty(name="rz",default=0)

    @classmethod
    def poll(cls, context):
        #check if there is an active object, check if we're not in edit mode
        return context.active_object is not None and context.mode == 'OBJECT'

    def invoke(self, context, event):
        ra_prefs = RHRingArray_get_preferences(bpy.context)
        self.number_of_objects = ra_prefs.count
        self.radius_of_circle = ra_prefs.radius
        self.apply_transform = ra_prefs.apply_transform
        self.delete_original = ra_prefs.delete_original
        self.linked_data = ra_prefs.linked_data
        self.create_parent = ra_prefs.create_parent
        self.merge_objects = ra_prefs.merge_objects
        self.autoAxis = ra_prefs.auto_axis
        return self.execute(context)

    
    def execute(self, context):
        selected_objects = bpy.context.selected_objects
        act_obj_ID = str(bpy.context.active_object.name)        
        act_obj = bpy.data.objects.get(act_obj_ID)
        array_loc = act_obj.location

        if act_obj.data.users > 1:
            act_obj.data.user_clear()
        if self.apply_transform:
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)                
        number_of_objects = self.number_of_objects
        radius_of_circle = self.radius_of_circle
        delete_original = self.delete_original
        offset_angle = self.offset_angle
        if self.autoAxis:
            hub_axis = quantAxis(self,context)
        else:
            hub_axis = self.hub_axis
        if self.merge_objects:
            self.create_parent = False
            self.linked_data = False

        clearSelection = bpy.ops.object.select_all(action='DESELECT')
        CreatedObjects = createRingArray(self,context,act_obj,hub_axis,offset_angle,number_of_objects)


        if self.create_parent:
            HubRot = (0,0,0)
            if hub_axis == "X": HubRot = (0,0, math.radians(90))
            if hub_axis == "Y": HubRot = (0,0,0)
            if hub_axis == "Z": HubRot = (math.radians(90),0,0)
            bpy.ops.object.empty_add(type='CIRCLE',radius = radius_of_circle,rotation = HubRot, location=array_loc)
            ringArray = bpy.context.active_object
            ringArray.name = "ringArray"
            ringArray.hide_render = True

        clearSelection

        for obj in CreatedObjects:
            if self.create_parent:
                obj.select_set(True)
                bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
                clearSelection
                ringArray.select_set(True)
            else:
                obj.select_set(True)

   

        act_obj = bpy.data.objects.get(act_obj_ID)

        if act_obj and act_obj.type in {"MESH"}:
            if self.merge_objects:
                bpy.ops.object.join()
                merged_mesh = bpy.context.active_object
                cursor_loc = bpy.context.scene.cursor.location
                bpy.context.scene.cursor.location = array_loc
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
                bpy.context.scene.cursor.location = cursor_loc

            if len(selected_objects) == 2 and self.merge_objects:
                try:
                    tgtObj = selected_objects[0]
                    modifier = tgtObj.modifiers.new(name='RABool',type="BOOLEAN")
                    modifier.operation = "DIFFERENCE"
                    modifier.solver = "FAST"
                    modifier.object = merged_mesh
                    tgtObj.select_set(True)
                    bpy.context.view_layer.objects.active = tgtObj
                    bpy.ops.object.modifier_apply(modifier="RABool")
                    clearSelection
                    merged_mesh.select_set(True)
                    bpy.ops.object.delete()
                except:
                    pass

        if delete_original:
            bpy.ops.object.select_all(action='DESELECT')
            act_obj = bpy.data.objects.get(act_obj_ID)
            act_obj.select_set(True)
            if act_obj.data.users > 1:
                act_obj.data.user_clear()
            bpy.ops.object.delete()          
 
        return {'FINISHED'}


    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Main")
        row = box.row()
        row.prop(self, "radius_of_circle",text="radius")
        row.prop(self, "number_of_objects",text ="count")
        row = box.row()
        row.prop(self, "offset_angle", text ="offset")
        row.prop(self, "resize",text="resize")

        box.prop(self, "autoAxis",text="Auto axis")
        if not self.autoAxis:
            box.prop(self, "hub_axis")

        box = layout.box()
        box.label(text="Tweak")       
        row = box.row()
        row.label(text="Rotate:")
        row.prop(self, "rx",text="X")
        row.prop(self, "ry",text="Y")
        row.prop(self, "rz",text="Z")

        box = layout.box()
        box.label(text="Options")
        row = box.row()
        row.prop(self, "apply_transform")
        row.prop(self, "delete_original")
        if not self.merge_objects:
            row = box.row()  
            row.prop(self, "create_parent")
            row.prop(self, "linked_data")
        row = box.row()
        row.prop(self, "merge_objects")
        row.operator("wm.operator_defaults",text ="Reset")


class RINGARRAY_OT_resetPreferences(Operator):
    """ Reset Add-on Preferences """
    bl_idname = "ringarray.reset_preferences"
    bl_label = "Reset Properties and Settings"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        rapreferences = context.preferences.addons[__name__].preferences
        rapreferences.property_unset("count")
        rapreferences.property_unset("radius")
        rapreferences.property_unset("create_parent")
        rapreferences.property_unset("linked_data")
        rapreferences.property_unset("merge_objects")
        rapreferences.property_unset("auto_axis")
        rapreferences.property_unset("delete_original")
        rapreferences.property_unset("apply_transform")
        return {'FINISHED'}

#create an npanel
class QOL_RingArrayPanel(Panel):
    bl_label = "QOL RingArray"
    bl_idname = "OBJECT_PT_qol_ringarray"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "QOL"

    def draw(self, context):
        ra_prefs = context.preferences.addons[__name__].preferences
        self.layout.operator("wm.qol_ringarray", text="QOL RingArray")
        self.layout.prop(ra_prefs, "count")

def draw(self, context):
    self.layout.operator("wm.qol_ringarray", text="QOL RingArray")

def register():
    bpy.utils.register_class(RH_RingArray_preferences)
    bpy.utils.register_class(RINGARRAY_OT_resetPreferences)
    bpy.utils.register_class(QOL_RingArrayPanel)
    bpy.utils.register_class(QOL_RingArray)
    
    bpy.types.VIEW3D_MT_object_context_menu.append(draw)

def unregister():
    bpy.utils.unregister_class(RH_RingArray_preferences)
    bpy.utils.unregister_class(RINGARRAY_OT_resetPreferences)
    bpy.utils.unregister_class(QOL_RingArrayPanel)
    bpy.utils.unregister_class(QOL_RingArray)
    bpy.types.VIEW3D_MT_object_context_menu.remove(draw)

if __name__ == "__main__":
    register()