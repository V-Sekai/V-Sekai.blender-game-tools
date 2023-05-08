bl_info = {
    'name': 'Camera PLUS',
    "author": "Max Derksen",
    'version': (1, 1, 1),
    'blender': (2, 83, 0),
    'location': 'VIEW 3D > Tools',
    #"warning": "This is a test version of the addon. Write in the discord channel(link below) about the errors.",
    "support": "COMMUNITY",
    'category': 'Object',
}

from . import (
    gizmo_group_button,
    transform_operators,
    tool,
    gizmo_group_tool,
    active_tool,
    cursor_gizmo,
    )



import bpy, sys, os, importlib  
from bpy.types import AddonPreferences

def visible_button(self, context):
    props = context.preferences.addons[__package__.split(".")[0]].preferences
    layout = self.layout
    layout.prop(props,'gizmo_visible',text='Show Button Camera Control')


class CAMGIZ_preferences(AddonPreferences):
    bl_idname = __package__


    def track_to(self, context):
        if self.target_visible:
            bpy.ops.camgiz.track_to('INVOKE_DEFAULT') # INVOKE_DEFAULT EXEC_DEFAULT



    tabs: bpy.props.EnumProperty(name="Tabs", items = [("GENERAL", "General", ""), ("KEYMAPS", "Keymaps", ""),], default="GENERAL")


    
    gizmo_visible: bpy.props.BoolProperty(name="Gizmo Visible", default=True)
    target_visible: bpy.props.BoolProperty(name="Target Visible", default=False, update=track_to)
    show_gizmo: bpy.props.BoolProperty(name="Visible Gizmo Cursor", default=False)

    
    def draw(self, context):
        layout = self.layout
        layout = self.layout

      
        #row = layout.row()
        #row.prop(self, "tabs", expand=True)

        box = layout.box()

        #if self.tabs == "GENERAL":
        self.draw_pivot_general(box)


        """ elif self.tabs == "KEYMAPS":
            self.draw_pivot_keymaps(context, box) """

    def draw_pivot_general(self, layout):
        pcoll = preview_collections["main"]
        market_icon = pcoll["market_icon"]
        gumroad_icon = pcoll["gumroad_icon"]
        artstation_icon = pcoll["artstation_icon"]
        discord_icon = pcoll["discord_icon"]
        #props = bpy.context.scene.props_auto_save

    
        #layout.prop(self, "small_button", text="Small Button")
        #layout.separator(factor=0.1)
        #layout.label(text="After changing the time settings, restart the AutoSave", icon='ERROR')
        #layout.prop(self, "time", text="Interval (minutes)")


        col = layout.column()
        col.label(text="Links")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("wm.url_open", text="Blender Market", icon_value=market_icon.icon_id).url = "https://blendermarket.com/creators/derksen"
        row.operator("wm.url_open", text="Gumroad", icon_value=gumroad_icon.icon_id).url = "https://gumroad.com/derksenyan"
        row.operator("wm.url_open", text="Artstation", icon_value=artstation_icon.icon_id).url = "https://www.artstation.com/derksen"
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("wm.url_open", text="Discord Channel", icon_value=discord_icon.icon_id).url = "https://discord.gg/SBEDbmK"


    def draw_pivot_keymaps(self, context, layout):
        col = layout.column()
        col.label(text="Keymap")
        #col = layout.column()
        
        #keymap = context.window_manager.keyconfigs.user.keymaps['Window']
        #keymap_items = keymap.keymap_items

        #col.prop(keymap_items['auto.auto_save'], 'type', text='Save New Version', full_event=True)
        
        col.label(text="Some hotkeys may not work because of the use of other addons", icon='ERROR')





preview_collections = {}
classes = [
    CAMGIZ_preferences,
]


 
def register():
    for cls in classes:
        bpy.utils.register_class(cls)


    
    pcoll = bpy.utils.previews.new()
    my_icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    pcoll.load("market_icon", os.path.join(my_icons_dir, "market.png"), 'IMAGE')
    pcoll.load("gumroad_icon", os.path.join(my_icons_dir, "gumroad.png"), 'IMAGE')
    pcoll.load("artstation_icon", os.path.join(my_icons_dir, "artstation.png"), 'IMAGE')
    pcoll.load("discord_icon", os.path.join(my_icons_dir, "discord.png"), 'IMAGE')
    preview_collections["main"] = pcoll

    bpy.types.VIEW3D_PT_overlay.append(visible_button)

    gizmo_group_button.register()
    transform_operators.register()
    tool.register()
    gizmo_group_tool.register()
    active_tool.register()
    cursor_gizmo.register()


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.types.VIEW3D_PT_overlay.remove(visible_button)

    gizmo_group_button.unregister()
    transform_operators.unregister()
    tool.unregister()
    gizmo_group_tool.unregister()
    active_tool.unregister()
    cursor_gizmo.unregister()