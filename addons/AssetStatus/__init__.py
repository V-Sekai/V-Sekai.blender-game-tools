bl_info = {
    "name": "Hard Surface Checklist",
    "description": "Checklist tool to help users through the hardsurface modelling process",
    "author": "Pilgrim",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Hard Surface Checklist Tab",
    "tracker_url": "https://twitter.com/ArtOfPilgrim",
    "support": 'COMMUNITY',
    "category": "3D View",
}

import bpy
import os

# Define panel to display dynamic status label
class VIEW3D_PT_MyStatusLabel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_my_status_label"
    bl_label = "Hard Surface Asset Checklist"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hard Surface Checklist"

    def draw(self, context):
        layout = self.layout
        mytool1 = context.scene.my_tool_1
        mytool2 = context.scene.my_tool_2
        mytool3 = context.scene.my_tool_3
        mytool4 = context.scene.my_tool_4
        mytool5 = context.scene.my_tool_5

        checklist_items = [mytool1.bullet_point_1, mytool1.bullet_point_2, mytool1.bullet_point_3,
                           mytool1.bullet_point_4, mytool2.bullet_point_5, mytool2.bullet_point_5a, mytool2.bullet_point_6, mytool2.bullet_point_6a,
                           mytool3.bullet_point_7, mytool3.bullet_point_7a, mytool3.bullet_point_8, mytool3.bullet_point_9, mytool3.bullet_point_9a, mytool3.bullet_point_9b,
                           mytool4.bullet_point_10, mytool4.bullet_point_10a, mytool4.bullet_point_11, mytool4.bullet_point_11a, mytool4.bullet_point_12, mytool4.bullet_point_12a, mytool4.bullet_point_12a,
                           mytool5.bullet_point_13, mytool5.bullet_point_14, mytool5.bullet_point_15, mytool5.bullet_point_16, mytool5.bullet_point_17, mytool5.bullet_point_18]

        checked_off_items = sum(checklist_items)

        progress_percentage = checked_off_items / len(checklist_items)

        # Draw the progress bar as a series of "|" characters
        progress_bar_length = 50  # adjust this for the desired length
        filled_length = int(progress_bar_length * progress_percentage)
        bar = '|' * filled_length + '-' * (progress_bar_length - filled_length)

        # Draw progress bar and percentage
        layout.label(text=f"Progress: [{bar}] {int(progress_percentage * 100)}%")

        if checked_off_items == 0:
            status_text = "Journey Starting"
            icon = 'AUTO'  # You can choose an appropriate icon here
        else:
            if mytool1.bullet_point_1 and mytool1.bullet_point_2 and mytool1.bullet_point_3 and mytool1.bullet_point_4:
                if mytool2.bullet_point_5 and mytool2.bullet_point_5a and mytool2.bullet_point_6 and mytool2.bullet_point_6a:
                    if mytool3.bullet_point_7 and mytool3.bullet_point_7a and mytool3.bullet_point_8 and mytool3.bullet_point_9 and mytool3.bullet_point_9a and mytool3.bullet_point_9b:
                        if mytool4.bullet_point_10 and mytool4.bullet_point_10a and mytool4.bullet_point_11 and mytool4.bullet_point_11a and mytool4.bullet_point_12 and mytool4.bullet_point_12a and mytool4.bullet_point_12b:
                            if mytool5.bullet_point_13 and mytool5.bullet_point_14 and mytool5.bullet_point_15 and mytool5.bullet_point_16 and mytool5.bullet_point_17 and mytool5.bullet_point_18:
                                status_text = "Good to go!"
                                icon = 'FUND'
                            else:
                                status_text = "Ready for Bake/Export"
                                icon = 'EXPORT'
                        else:
                            status_text = "Ready for UV'ing"
                            icon = 'UV'
                    else:
                        status_text = "Ready for Low Poly"
                        icon = 'IPO_CONSTANT'
                else:
                    status_text = "Ready for High Poly"
                    icon = 'MOD_SUBSURF'
            else:
                status_text = "Journey Started"
                icon = 'AUTO'    

        layout.label(text=status_text, icon=icon)



# Define properties for first set of bullet points
class MySettingsPropertyGroup1(bpy.types.PropertyGroup):
    bullet_point_1: bpy.props.BoolProperty(name="Everything Blocked Out", description="Everything that needs blocked out for testing has been created")
    bullet_point_2: bpy.props.BoolProperty(name="No Flipped Faces or holes", description="Check mesh isn't inverted from mirrored geo and no holes in mesh")
    bullet_point_3: bpy.props.BoolProperty(name="Clean Topology", description="Ensure topology is clean, with quads and proper use of triangles/n-gons")
    bullet_point_4: bpy.props.BoolProperty(name="Correct Scale", description="Check that the model's scale is consistent with real-world dimensions & in engine")

# Define properties for second set of bullet points
class MySettingsPropertyGroup2(bpy.types.PropertyGroup):
    bullet_point_5: bpy.props.BoolProperty(name="Parts ≤5M Tri's", description="Toolbag can find it difficult to bake if each HP part is more than 5 million polygons - but this may change, good practice either way")
    bullet_point_5a: bpy.props.BoolProperty(name="Parts Suffixed '_HP'", description="Each part needs to be appropriately named ending in _HP")
    bullet_point_6: bpy.props.BoolProperty(name="Everything Detailed", description="Make sure each part has been appropriately detailed")
    bullet_point_6a: bpy.props.BoolProperty(name="Weighted Normals Check", description="Sometimes this can help fix normal issues")

# Define properties for third set of bullet points
class MySettingsPropertyGroup3(bpy.types.PropertyGroup):
    bullet_point_7: bpy.props.BoolProperty(name="Everything Has a LP", description="Check that every HP part has a LP part")
    bullet_point_7a: bpy.props.BoolProperty(name="Unwelded Vert Check", description="Make sure there's no unwelded verts")
    bullet_point_8: bpy.props.BoolProperty(name="Parts Suffixed '_LP'", description="Each part name needs to correspond to its HP name + ending in _LP")
    bullet_point_9: bpy.props.BoolProperty(name="Scale & Transforms Reset", description="Make sure there's no odd rotations or scaling")
    bullet_point_9a: bpy.props.BoolProperty(name="Data & Mesh Names Match", description="has to have the matching dataname and mesh name for each object to export properly")
    bullet_point_9b: bpy.props.BoolProperty(name="Mirrored/Copied Parts", description="Don't make unnecessary LP meshes that can be either mirrored or copied over")

# Define properties for fourth set of bullet points
class MySettingsPropertyGroup4(bpy.types.PropertyGroup):
    bullet_point_10: bpy.props.BoolProperty(name="Seams & Unwrapped", description="Make sure seams are hidden as best as possible & everything is unwrapped properly")
    bullet_point_10a: bpy.props.BoolProperty(name="Proper Pixel Padding/Margin", description="1024 = 4px padding/2px • margin 2048 = 8px padding/4px margin • 4096 = 16px padding/8px margin")
    bullet_point_11: bpy.props.BoolProperty(name="Mirrored/Copied Parts Offset", description="Make any mirrored or copied parts of the mesh are properly offset in the UV by 1 to prevent baking issues")
    bullet_point_11a: bpy.props.BoolProperty(name="Proper Scale & Texel Density", description="make sure UV Islands are scaled properly, and the texture size will be appropriate for the scale of the asset")
    bullet_point_12: bpy.props.BoolProperty(name="Hard Edges at UV Seams", description="every hard edge is a uv seam, but not every seam is a hard edge") 
    bullet_point_12a: bpy.props.BoolProperty(name="Check For Stretching", description="Make sure there's no stretching in the UV")
    bullet_point_12b: bpy.props.BoolProperty(name="UV Channel Check", description="Is the asset using multiple UV's? Are both UV'd?")

# Define properties for fifth set of bullet points
class MySettingsPropertyGroup5(bpy.types.PropertyGroup):
    bullet_point_13: bpy.props.BoolProperty(name="Transforms at 0", description="Make sure everything is zero'd out Location/Rotation/Scaling")
    bullet_point_14: bpy.props.BoolProperty(name="Hard Edges at UV Seams", description="Double check!")
    bullet_point_15: bpy.props.BoolProperty(name="Check for Skewing Normals", description="look over any baked in details for skewing & fix")
    bullet_point_16: bpy.props.BoolProperty(name="No Penetrating AO/Normals", description="if the offset distance isn't right this will happen")
    bullet_point_17: bpy.props.BoolProperty(name="Check Mirrored/Copied Parts", description="Make sure there's no strange artifacts/shading on these parts")
    bullet_point_18: bpy.props.BoolProperty(name="Mesh Triangulated", description="Either add a triangulation mod before or on export")

# Mid poly checklist panel
class VIEW3D_PT_MyPanel1(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_my_panel_1"
    bl_label = "Base Mesh/Mid Poly"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hard Surface Checklist"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='MESH_CUBE') 

    def draw(self, context):
        layout = self.layout
        mytool = context.scene.my_tool_1
        box = layout.box()
        box.prop(mytool, "bullet_point_1")
        box.prop(mytool, "bullet_point_2")
        box.prop(mytool, "bullet_point_3")
        box.prop(mytool, "bullet_point_4")

# High Poly checklist panel
class VIEW3D_PT_MyPanel2(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_my_panel_2"
    bl_label = "High Poly"
    bl_icon = 'MOD_SUBSURF'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hard Surface Checklist"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='MOD_SUBSURF')

    def draw(self, context):
        layout = self.layout
        mytool = context.scene.my_tool_2
        box = layout.box()
        box.prop(mytool, "bullet_point_5")
        box.prop(mytool, "bullet_point_5a")
        box.prop(mytool, "bullet_point_6")
        box.prop(mytool, "bullet_point_6a")

# Low Poly checklist panel
class VIEW3D_PT_MyPanel3(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_my_panel_3"
    bl_label = "Low Poly"
    bl_icon = 'IPO_CONSTANT'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hard Surface Checklist"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='IPO_CONSTANT')

    def draw(self, context):
        layout = self.layout
        mytool = context.scene.my_tool_3
        box = layout.box()
        box.prop(mytool, "bullet_point_7")
        box.prop(mytool, "bullet_point_7a")
        box.prop(mytool, "bullet_point_8")
        box.prop(mytool, "bullet_point_9")
        box.prop(mytool, "bullet_point_9a")
        box.prop(mytool, "bullet_point_9b")

# UV checklist panel
class VIEW3D_PT_MyPanel4(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_my_panel_4"
    bl_label = "UV"
    bl_icon = 'GROUP_UVS'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hard Surface Checklist"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='UV')

    def draw(self, context):
        layout = self.layout
        mytool = context.scene.my_tool_4
        box = layout.box()
        box.prop(mytool, "bullet_point_10")
        box.prop(mytool, "bullet_point_10a")
        box.prop(mytool, "bullet_point_11")
        box.prop(mytool, "bullet_point_11a")
        box.prop(mytool, "bullet_point_12")
        box.prop(mytool, "bullet_point_12a")
        box.prop(mytool, "bullet_point_12b")

# Bake/export checklist panel
class VIEW3D_PT_MyPanel5(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_my_panel_5"
    bl_label = "Bake/Export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hard Surface Checklist"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='EXPORT')

    def draw(self, context):
        layout = self.layout
        mytool = context.scene.my_tool_5
        box = layout.box()
        box.prop(mytool, "bullet_point_13")
        box.prop(mytool, "bullet_point_14")
        box.prop(mytool, "bullet_point_15")
        box.prop(mytool, "bullet_point_16")
        box.prop(mytool, "bullet_point_17")
        box.prop(mytool, "bullet_point_18")

# Actions checklist panel
class VIEW3D_PT_ChecklistActions(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_checklist_actions"
    bl_label = "Checklist Actions"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hard Surface Checklist"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='TRIA_RIGHT')

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator("my_tool.clear_all", text="Clear All")


# Operator to clear all checklist items
class MYTOOL_OT_ClearAll(bpy.types.Operator):
    bl_idname = "my_tool.clear_all"
    bl_label = "Clear All"

    def execute(self, context):
        # Reset all checklist items to False
        context.scene.my_tool_1.bullet_point_1 = False
        context.scene.my_tool_1.bullet_point_2 = False
        context.scene.my_tool_1.bullet_point_3 = False
        context.scene.my_tool_1.bullet_point_4 = False
        context.scene.my_tool_2.bullet_point_5 = False
        context.scene.my_tool_2.bullet_point_5a = False
        context.scene.my_tool_2.bullet_point_6 = False
        context.scene.my_tool_2.bullet_point_6a = False
        context.scene.my_tool_3.bullet_point_7 = False
        context.scene.my_tool_3.bullet_point_7a = False
        context.scene.my_tool_3.bullet_point_8 = False
        context.scene.my_tool_3.bullet_point_9 = False
        context.scene.my_tool_3.bullet_point_9a = False
        context.scene.my_tool_3.bullet_point_9b = False
        context.scene.my_tool_4.bullet_point_10 = False
        context.scene.my_tool_4.bullet_point_10a = False
        context.scene.my_tool_4.bullet_point_11 = False
        context.scene.my_tool_4.bullet_point_11a = False
        context.scene.my_tool_4.bullet_point_12 = False
        context.scene.my_tool_4.bullet_point_12a = False
        context.scene.my_tool_4.bullet_point_12b = False
        context.scene.my_tool_5.bullet_point_13 = False
        context.scene.my_tool_5.bullet_point_14 = False
        context.scene.my_tool_5.bullet_point_15 = False
        context.scene.my_tool_5.bullet_point_16 = False
        context.scene.my_tool_5.bullet_point_17 = False
        context.scene.my_tool_5.bullet_point_18 = False

        return {'FINISHED'}


class VIEW3D_PT_UsefulTools(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_useful_tools"
    bl_label = "Useful Tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hard Surface Checklist"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='TOOL_SETTINGS')

    def draw(self, context):
        layout = self.layout

        # Button for the human scale reference tool with an icon
        row = layout.row()
        row.operator("object.import_human_scale_ref", text="Import Human Scale Ref", icon='MOD_LENGTH')

        # Row for Unit System dropdown
        row = layout.row()
        row.label(text="Unit System:")
        row.prop(context.scene.unit_settings, "system", text="")

        # Row for Length Units dropdown, only if Unit System is Metric or Imperial
        if context.scene.unit_settings.system in {'METRIC', 'IMPERIAL'}:
            row = layout.row()
            row.label(text="Length Unit:")
            row.prop(context.scene.unit_settings, "length_unit", text="")

        # ... Add more tools as needed ...

class OBJECT_OT_ImportHumanScaleRef(bpy.types.Operator):
    """Import a human scale reference object"""
    bl_idname = "object.import_human_scale_ref"
    bl_label = "Import Human Scale Ref"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Path to the current script (__init__.py)
        script_file = os.path.realpath(__file__)
        script_dir = os.path.dirname(script_file)

        # Path to the FBX file "Free Base Mesh" (https://skfb.ly/YZ9Z) by angelaxiotis is licensed under Creative Commons Attribution (http://creativecommons.org/licenses/by/4.0/).
        fbx_path = os.path.join(script_dir, "resources", "HumanScaleRef.fbx")

        # Import the FBX file
        bpy.ops.import_scene.fbx(filepath=fbx_path)

        # Get the collection name
        collection_name = "Human Scale Ref"

        # Check if the collection exists
        if collection_name in bpy.data.collections:
            # Get the collection
            collection = bpy.data.collections[collection_name]
        else:
            # Create a new collection
            collection = bpy.data.collections.new(collection_name)
            # Add the collection to the Blender scene
            bpy.context.scene.collection.children.link(collection)

        # Get the newly imported object
        imported_obj = bpy.context.selected_objects[0] if bpy.context.selected_objects else None

        if not imported_obj:
            self.report({'ERROR'}, "Failed to import the object.")
            return {'CANCELLED'}

        # Set the imported object as the active object
        bpy.context.view_layer.objects.active = imported_obj

        # Make sure the object is selected
        imported_obj.select_set(True)

        # Apply all transforms
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Unlink the object from its original collection
        for coll in imported_obj.users_collection:
            coll.objects.unlink(imported_obj)

        # Link the object to the new collection
        collection.objects.link(imported_obj)

        # Deselect all objects and clear the active object
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = None

        return {'FINISHED'}


# Useful resource links panel
class VIEW3D_PT_ResourceLinks(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_resource_links"
    bl_label = "Resource Links"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hard Surface Checklist"

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon='URL')

    def draw(self, context):
        layout = self.layout

        # UI elements for each link
        layout.label(text="Useful Documentation:")

        col = layout.column()
        col.operator("wm.url_open", text="Texel Density").url = "https://www.beyondextent.com/deep-dives/deepdive-texeldensity" 

        col.operator("wm.url_open", text="Low Poly & Bake Theory").url = "https://www.artstation.com/learning/courses/bb6/low-poly-and-bake/chapters/4QPr/low-poly-theory"

        col.operator("wm.url_open", text="Weapon Ref Library").url = "https://dinustyempire.notion.site/6-1-Weapons-library-0ab1d28137e749f0abfca738d93a9222"
        
        col.operator("wm.url_open", text="SubD References").url = "http://wiki.polycount.com/wiki/Subdivision_Surface_Modeling#Tips_.26_Tricks"

        col.operator("wm.url_open", text="Weapon Breakdown").url = "https://gamesartist.co.uk/aks-74u-maximov/"

        col.operator("wm.url_open", text="Prop Breakdown").url = "https://gamesartist.co.uk/fixed-carbine-stock/"

        # Add UI elements for each link
        layout.label(text="Contact & Community:")

        col = layout.column()
        col.operator("wm.url_open", text="Pilgrims' Twitter").url = "https://twitter.com/ArtOfPilgrim"

        col.operator("wm.url_open", text="Pilgrims' Youtube").url = "https://www.youtube.com/@ArtOfPilgrim"

        col.operator("wm.url_open", text="Discord").url = "https://dsc.gg/pilgrim"
        # Add more links as needed

    
def register():
    bpy.utils.register_class(VIEW3D_PT_MyStatusLabel)
    bpy.utils.register_class(MySettingsPropertyGroup1)
    bpy.utils.register_class(MySettingsPropertyGroup2)
    bpy.utils.register_class(MySettingsPropertyGroup3)
    bpy.utils.register_class(MySettingsPropertyGroup4)
    bpy.utils.register_class(MySettingsPropertyGroup5)
    bpy.types.Scene.my_tool_1 = bpy.props.PointerProperty(type=MySettingsPropertyGroup1)
    bpy.types.Scene.my_tool_2 = bpy.props.PointerProperty(type=MySettingsPropertyGroup2)
    bpy.types.Scene.my_tool_3 = bpy.props.PointerProperty(type=MySettingsPropertyGroup3)
    bpy.types.Scene.my_tool_4 = bpy.props.PointerProperty(type=MySettingsPropertyGroup4)
    bpy.types.Scene.my_tool_5 = bpy.props.PointerProperty(type=MySettingsPropertyGroup5)
    bpy.utils.register_class(VIEW3D_PT_MyPanel1)
    bpy.utils.register_class(VIEW3D_PT_MyPanel2)
    bpy.utils.register_class(VIEW3D_PT_MyPanel3)
    bpy.utils.register_class(VIEW3D_PT_MyPanel4)
    bpy.utils.register_class(VIEW3D_PT_MyPanel5)
    bpy.utils.register_class(VIEW3D_PT_ChecklistActions)
    bpy.utils.register_class(MYTOOL_OT_ClearAll)
    bpy.utils.register_class(VIEW3D_PT_UsefulTools)
    bpy.utils.register_class(OBJECT_OT_ImportHumanScaleRef)
    bpy.utils.register_class(VIEW3D_PT_ResourceLinks)


def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_MyStatusLabel)
    del bpy.types.Scene.my_tool_1
    del bpy.types.Scene.my_tool_2
    del bpy.types.Scene.my_tool_3
    del bpy.types.Scene.my_tool_4
    del bpy.types.Scene.my_tool_5
    bpy.utils.unregister_class(MySettingsPropertyGroup1)
    bpy.utils.unregister_class(MySettingsPropertyGroup2)
    bpy.utils.unregister_class(MySettingsPropertyGroup3)
    bpy.utils.unregister_class(MySettingsPropertyGroup4)
    bpy.utils.unregister_class(MySettingsPropertyGroup5)
    bpy.utils.unregister_class(VIEW3D_PT_MyPanel1)
    bpy.utils.unregister_class(VIEW3D_PT_MyPanel2)
    bpy.utils.unregister_class(VIEW3D_PT_MyPanel3)
    bpy.utils.unregister_class(VIEW3D_PT_MyPanel4)
    bpy.utils.unregister_class(VIEW3D_PT_MyPanel5)
    bpy.utils.unregister_class(VIEW3D_PT_ChecklistActions)
    bpy.utils.unregister_class(MYTOOL_OT_ClearAll)
    bpy.utils.unregister_class(VIEW3D_PT_UsefulTools)
    bpy.utils.unregister_class(OBJECT_OT_ImportHumanScaleRef)
    bpy.utils.unregister_class(VIEW3D_PT_ResourceLinks)


if __name__ == "__main__":
    register()