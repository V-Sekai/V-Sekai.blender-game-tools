import bpy,blf

class DrawText:
    def __init__(self,context,scale=1,x_offset=0,fontcolor=(1,0,1,0.8),y_offset=0,inputString="",):
        self.fontcolor = fontcolor
        self.inputString = inputString
        self.scale = scale
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.handle = bpy.types.SpaceView3D.draw_handler_add(
                   self.draw_text_callback,(context,),
                   'WINDOW', 'POST_PIXEL')
    def draw_text_callback(self, context):
        font_id = 0
        blf.size(font_id, int(0.6 * self.scale))
        x = int(self.x_offset)
        y = int(50 + self.y_offset)
        blf.color(font_id,self.fontcolor[0],self.fontcolor[1],self.fontcolor[2],self.fontcolor[3])
        blf.position(font_id, x,y,0)
        blf.draw(font_id, (self.inputString))
    def remove_handle(self):
        bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')


def KillQOLHud():
    keys_to_remove = [key for key in bpy.app.driver_namespace if key.startswith("QOL_")]
    for key in keys_to_remove:
        if bpy.app.driver_namespace[key] is not None:
            if bpy.app.driver_namespace[key].handle is not None:
                bpy.app.driver_namespace[key].remove_handle()
            del bpy.app.driver_namespace[key]

def QHColors():
    QHColrs = { "BrandName":(1,0.45,0.05,1),
                "TopText":(0.83,0.85,0.9,0.8),
                "LowerText":(0.83,0.85,0.9,0.3),
                "HelpText":(1,1,1,1),
                "HelpDescr":(.8,.8,.8,1),}
    return QHColrs

def draw_Hud_PolyPal(self,context):
    KillQOLHud()
    QOLHud = bpy.app.driver_namespace
    EndX = context.area.width
    MidX = EndX * 0.5
    QHColrs = QHColors()
    QOLHud["QOL_Hud_BrandName"] = DrawText(context,40,(MidX-110),QHColrs["BrandName"],0,     "QOL "  ,)
    QOLHud["QOL_Hud_TopText"]   = DrawText(context,40,(MidX-50),QHColrs["TopText"],0,        "PolyPal Drawing",)                                                
    QOLHud["QOL_Hud_LowerText"] = DrawText(context,32,(MidX-115),QHColrs["LowerText"] ,-25,  "TAB, RMB, ESC tool to finish",)

    QOLHud["QOL_HelpLine1A"] = DrawText(context,22,(EndX-220),QHColrs["HelpText"] ,55,       "Left Mouse:",)
    QOLHud["QOL_HelpLine1B"] = DrawText(context,22,(EndX-100),QHColrs["HelpDescr"] ,55,      "Place vertex",)
    QOLHud["QOL_HelpLine2A"] = DrawText(context,22,(EndX-220),QHColrs["HelpText"] ,40,       "Middle:",)
    QOLHud["QOL_HelpLine2B"] = DrawText(context,22,(EndX-100),QHColrs["HelpDescr"] ,40,      "Bevel",)
    QOLHud["QOL_HelpLine3A"] = DrawText(context,22,(EndX-220),QHColrs["HelpText"] ,25,       "    +C:",)
    QOLHud["QOL_HelpLine3B"] = DrawText(context,22,(EndX-100),QHColrs["HelpDescr"] ,25,      "(C)hamfer",)
    QOLHud["QOL_HelpLine4A"] = DrawText(context,22,(EndX-220),QHColrs["HelpText"] ,10,       "    +F:",)
    QOLHud["QOL_HelpLine4B"] = DrawText(context,22,(EndX-100),QHColrs["HelpDescr"] ,10,      "(F)illet",)
    QOLHud["QOL_HelpLine5A"] = DrawText(context,22,(EndX-220),QHColrs["HelpText"] ,-5,       "Shift(Drag):",)
    QOLHud["QOL_HelpLine5B"] = DrawText(context,22,(EndX-100),QHColrs["HelpDescr"] ,-5,      "Freehand",)
    QOLHud["QOL_HelpLine6A"] = DrawText(context,22,(EndX-220),QHColrs["HelpText"] ,-20,      "X: (in ortho)",)
    QOLHud["QOL_HelpLine6B"] = DrawText(context,22,(EndX-100),QHColrs["HelpDescr"] ,-20,     "Toggle Grid",)
    QOLHud["QOL_HelpLine7A"] = DrawText(context,22,(EndX-220),QHColrs["HelpText"] ,-35,      "ALT Click",)
    QOLHud["QOL_HelpLine7B"] = DrawText(context,22,(EndX-100),QHColrs["HelpDescr"] ,-35,     "Delete Vertex",)
    context.area.tag_redraw()

def draw_Hud_Rectangle(self,context):
    KillQOLHud()
    QOLHud = bpy.app.driver_namespace
    EndX = context.area.width
    MidX = EndX * 0.5
    QHColrs = QHColors()
    QOLHud["QOL_Hud_BrandName"] = DrawText(context,40,(MidX-118),QHColrs["BrandName"],0,     "QOL "  ,)
    QOLHud["QOL_Hud_TopText"]   = DrawText(context,40,(MidX-58),QHColrs["TopText"],0,        "PolyPal Rectangle",)                                                
    QOLHud["QOL_Hud_LowerText"] = DrawText(context,32,(MidX-115),QHColrs["LowerText"] ,-25,  "TAB, RMB, ESC tool to finish",)
    context.area.tag_redraw()

def draw_Hud_Circle(self,context):
    KillQOLHud()
    QOLHud = bpy.app.driver_namespace
    EndX = context.area.width
    MidX = EndX * 0.5
    QHColrs = QHColors()
    QOLHud["QOL_Hud_BrandName"] = DrawText(context,40,(MidX-110),QHColrs["BrandName"],0,     "QOL "  ,)
    QOLHud["QOL_Hud_TopText"]   = DrawText(context,40,(MidX-50),QHColrs["TopText"],0,        "PolyPal Circle",)                                                
    QOLHud["QOL_Hud_LowerText"] = DrawText(context,32,(MidX-115),QHColrs["LowerText"] ,-25,  "TAB, RMB, ESC tool to finish",)
    context.area.tag_redraw()
