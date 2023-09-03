from bpy.types import AddonPreferences, Context, UILayout


class BaseAddonPreferences(AddonPreferences):
    bl_idname: str # addon's root __package__
    layout: UILayout
    
    def draw(self, context: Context) -> None:
        self.draw_ui(context, self.layout)
        
    def draw_ui(self, context: Context, layout: UILayout) -> None:
        pass        
