bl_info = {
    "name": "QOL Materials Panel",
    "author": "Rico Holmes",
    "version": (1, 20, 4),
    "blender": (3, 2, 0),
    "description": "Materials Utilities panel",
    "category": "Interface",
}

import bpy
from bpy.props import (StringProperty,BoolProperty,)
from bpy.types import (Panel,Operator)

from .prefs import *
from .functions import *
bpy.utils.register_class(RH_Materials_Panel_preferences)
rhmp_prefs = bpy.context.preferences.addons[__package__].preferences

bpy.types.Scene.rndm_color = BoolProperty(
    name="Random color",
        description="add random color when creating new material",
        default = True)
bpy.types.Scene.blitz = BoolProperty(
    name="Overwrite",
        description="add random color when creating new material",
        default = True)
bpy.types.Scene.filterString= StringProperty(
    name = 'Filter',
    options={'TEXTEDIT_UPDATE'},
                )

class RicosMaterialsPanel(Panel):
    """Creates a Panel in the Object properties area"""
    bl_label = "QOL Materials Panel"
    bl_idname = "OBJECT_PT_rhmaterials"
    if rhmp_prefs.paneltype == "properties":
        bl_space_type = 'PROPERTIES'
        bl_region_type = 'WINDOW'
        bl_context = "material"
    if rhmp_prefs.paneltype == "npanel": 
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = "QOL Mats"  


    def draw(self, context):
        
        materials = bpy.data.materials.items()
        bl_idapply = RHApplyMaterial.bl_idname
        bl_idgrab = RHSelectObjsWithMaterial.bl_idname
        bl_idnewmat = RHAddNewMaterial.bl_idname
        bl_iddeletemat = RHDeleteMat.bl_idname
        bl_idcleanoutmats = RHCleanoutUnusedMats.bl_idname
        bl_idpurgeunusedmats = RHPurgeUnusedMats.bl_idname

        layout = self.layout
        row = layout.grid_flow()
        row.operator(bl_idnewmat,text="New Material",icon="MATSHADERBALL")
        row.prop(context.scene,"filterString",text="",icon="VIEWZOOM")
        row.prop(context.scene,"rndm_color")
        row.prop(context.scene,"blitz")
        row.prop(rhmp_prefs,"show_swatch")

        row = layout.row(align = True)
        row.operator(bl_idcleanoutmats,text="Cleanup",)
        row.operator(bl_idpurgeunusedmats,text="Purge Unused",)
        col = layout.column(align=True)
        for material_name, material in materials:
            material.preview_ensure()
            if material_name not in {"Dots Stroke"}:
                if context.scene.filterString.lower() in material_name.lower():
                    # col.separator()
                    contents = col.grid_flow()
                    leftBox = contents.box()
                    
                    row = leftBox.row(align=True) 
                    if material.preview:
                        op_Apply = row.operator(bl_idapply,text ="",icon_value = material.preview.icon_id)
                    else:
                        op_Apply = row.operator(bl_idapply,text ="",icon='MATSPHERE')
                    op_Apply.material_name = material_name
                    row.prop(material,"name",text="")
                    rightBox = contents.box()
                    row = rightBox.row(align=True)
                    if rhmp_prefs.show_swatch:
                        row.ui_units_x = 2
                    if rhmp_prefs.show_fakeuser:
                        row.prop(material,"use_fake_user",text="")
                    if rhmp_prefs.show_swatch:
                        if material.use_nodes:
                            try:
                                if material.node_tree.nodes[0].inputs[0].default_value:
                                    row.prop(material.node_tree.nodes[0].inputs[0],"default_value",text = "")
                                pass
                            except: 
                                row.label(text = " ")
                                pass
                    if rhmp_prefs.show_delete:
                        op_Delete = row.operator(bl_iddeletemat,text="",icon='TRASH')
                        op_Delete.material_name = material_name
                    if rhmp_prefs.show_grab:
                        isUsed = checkUsed(context,material)
                        if isUsed:                        
                            op_Grab = row.operator(bl_idgrab,text="",icon="RADIOBUT_ON")
                        else: op_Grab = row.operator(bl_idgrab,text="",icon="RADIOBUT_OFF")
                        op_Grab.material_name = material_name






#----------------------------------------------------------------------------------
class RHDeleteMat(Operator):
    """Add and apply new material"""
    bl_idname = "view3d.rhdeletemat"
    bl_label = "delete material"
    bl_options = {'REGISTER', 'UNDO'}
    material_name: StringProperty(
            name = 'Material Name',
            description = 'Name of Material to find and Select',
            maxlen = 63
            )
    @classmethod
    def poll(cls,context):
        return context.active_object != None
    def execute(self, context):
        origActive = bpy.context.view_layer.objects.active
        all_original_selected = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = None
        mat = bpy.data.materials[self.material_name]
        bpy.data.materials.remove(mat,do_unlink=True)
        deleteUnusedMatSlotMats()
        for obj in all_original_selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = origActive
        return{"FINISHED"}
#----------------------------------------------------------------------------------
class RHPurgeUnusedMats(Operator):
    """Add and apply new material"""

    bl_idname = "view3d.purgeunusedmats"
    bl_label = "add material"
    bl_context = "object"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls,context):
        return context.active_object != None
    def execute(self, context):    
        mat = bpy.data.materials
        for mat in bpy.data.materials:
            if mat.users == 0:
                bpy.data.materials.remove(mat,do_unlink=True)
        return{"FINISHED"}
#----------------------------------------------------------------------------------
class RHAddNewMaterial(Operator):
    """Add and apply new material. \nCTRL Click to add random new material to each object selected"""

    bl_idname = "view3d.rhaddnewmaterial"
    bl_label = "add material"
    bl_context = "object"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty(
            name = 'Material Name',
            description = 'Name of Material to find and Select',
            maxlen = 63
            )
    @classmethod
    def poll(cls,context):
        return context.active_object != None
    def invoke(self, context,event):   
        if event.ctrl:
            all_original_selected = bpy.context.selected_objects
            for obj in all_original_selected:
                bpy.ops.object.mode_set(mode = 'OBJECT')        
                bpy.ops.object.select_all(action='DESELECT')
                if obj.type in {'MESH',"CURVE"}:
                    activelyr = bpy.context.view_layer
                    if obj.name in activelyr.objects:
                        obj.select_set(True)
                    matGenerator(context)
                    # obj.data.update()
            for obj in all_original_selected:
                bpy.context.view_layer.objects.active = obj
                activelyr = bpy.context.view_layer
                if obj.name in activelyr.objects:
                    obj.select_set(True)       
        else:
            matGenerator(context)
            context.area.tag_redraw()
        return{"FINISHED"}

    def execute(self,context):
        matGenerator(context)
        return{"FINISHED"}
#----------------------------------------------------------------------------------
class RHCleanoutUnusedMats(Operator):
    """Add and apply new material"""
    bl_idname = "view3d.rhcleanoutmats"
    bl_label = "remove unused materials from selected objects"
    bl_context = "object"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls,context):
        return context.active_object != None
    def execute(self, context):    
        allObjects = bpy.context.selected_objects
        for obj in allObjects:
            indices_used=[]
            indices_unused=[]
            protected_mats=[]
            for x in obj.data.polygons:
                if x.material_index not in indices_used:
                    indices_used.append(x.material_index)
            for slot in obj.material_slots:
                if slot.slot_index not in indices_used:
                    indices_unused.append(slot.slot_index)
            indices_unused.sort()
            indices_unused.reverse()

            for i in indices_unused:
                obj.active_material_index = i
                bpy.ops.object.material_slot_remove()
            # now purge the universe of these unused material slots!!
            deleteUnusedMatSlotMats()
        return{"FINISHED"}
#----------------------------------------------------------------------------------

class RHSelectObjsWithMaterial(Operator):
    """Select all objects with this material"""

    bl_idname = "view3d.rhselobjswithmaterial"
    bl_label = "grab"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty(
            name = 'Material Name',
            description = 'Name of Material to find and Select',
            maxlen = 63
            )
    @classmethod
    def poll(cls,context):
        return context.active_object != None
    def execute(self, context):
        bpy.ops.object.mode_set(mode = 'OBJECT')        
        bpy.ops.object.select_all(action='DESELECT')
        allObjects = bpy.data.objects
        thisMat = bpy.data.materials.get(self.material_name)
        for obj in allObjects:
            if obj.type in {"MESH","CURVE"}:
                stepper = 0
                for mat in obj.data.materials:
                    if mat == thisMat:
                        obj.active_material_index = stepper
                        activelyr = bpy.context.view_layer
                        if obj.name in activelyr.objects:
                            obj.select_set(True)
                    stepper += 1
        return{"FINISHED"}
#----------------------------------------------------------------------------------




class RHApplyMaterial(Operator):
    """Apply material to selected object. \nCTRL click to duplicate material"""

    bl_idname = "view3d.rhapplymaterial"
    bl_label = "apply material"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty(
            name = 'Material Name',
            description = 'Name of Material to find and Select',
            maxlen = 63
            )
    @classmethod
    def poll(cls,context):
        return context.active_object != None


    def invoke(self, context,event):   
        if event.ctrl:
            dupeMat(self.material_name)
        else:
            applyThisMat(self.material_name)
        
        return{"FINISHED"}

    def execute(self, context):
        applyThisMat(self.material_name)
        return{"FINISHED"}

#----------------------------------------------------------------------------------
def register():
    bpy.utils.register_class(RicosMaterialsPanel)
    bpy.utils.register_class(RHCleanoutUnusedMats)
    bpy.utils.register_class(RHPurgeUnusedMats)
    bpy.utils.register_class(RHApplyMaterial)
    bpy.utils.register_class(RHSelectObjsWithMaterial)
    bpy.utils.register_class(RHAddNewMaterial)
    bpy.utils.register_class(RHDeleteMat)    
def unregister():
    bpy.utils.unregister_class(RH_Materials_Panel_preferences)
    bpy.utils.unregister_class(RicosMaterialsPanel)
    bpy.utils.unregister_class(RHCleanoutUnusedMats)
    bpy.utils.unregister_class(RHPurgeUnusedMats)
    bpy.utils.unregister_class(RHApplyMaterial)
    bpy.utils.unregister_class(RHSelectObjsWithMaterial)
    bpy.utils.unregister_class(RHAddNewMaterial)
    bpy.utils.unregister_class(RHDeleteMat)
    
if __name__ == "__main__":
    register()
