import bpy,random
import numpy as np
def matGenerator(context):
    NuMaterial = bpy.data.materials.new("New Material")
    NuMaterial.use_nodes = True
    rndcl: FloatVectorProperty(
    name = 'random color',
    subtype = 'COLOR',
    size = 4,
    description = 'base for random color so we get gamma corrected output',
    maxlen = 63
    )
    allCurrentMats = []
    for x in bpy.data.materials:
        allCurrentMats.append(x.name)
    if context.scene.rndm_color is True:
        randoColorTuple = RHNamedRandomColor(allCurrentMats)
        NuMaterial.name = (randoColorTuple[0])
        rndclValue = (randoColorTuple[1])
        rndcl = (rndclValue[0],rndclValue[1],rndclValue[2],1)
        NuMaterial.node_tree.nodes["Principled BSDF"].inputs[0].default_value = rndcl
        NuMaterial.diffuse_color = rndcl
    applyThisMat(NuMaterial.name)

#---------------------------------------------------------------------------------- 

def checkUsed(context,thisMat):
    for obj in bpy.context.selected_objects:
        if obj.type in {"MESH","CURVE"}:
            for mat in obj.data.materials:
                if mat == thisMat:
                    return True
                    break
    return False

#---------------------------------------------------------------------------------- 
def deleteUnusedMatSlotMats():
    origActive = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = None
    all_original_selected = bpy.context.selected_objects
    bpy.ops.object.select_all(action='DESELECT')
    allObjects = bpy.data.objects
    for obj in allObjects:
        if(obj.type in {'MESH','CURVE'}):
            activelyr = bpy.context.view_layer
            if obj.name in activelyr.objects:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.material_slot_remove_unused()
                bpy.context.view_layer.objects.active = None
                obj.select_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in all_original_selected:
        activelyr = bpy.context.view_layer
        if obj.name in activelyr.objects:
            obj.select_set(True)
    for obj in allObjects:
        if(obj.type in {'MESH'}):
            obj.data.update
    bpy.context.view_layer.objects.active = origActive
#----------------------------------------------------------------------------------    

def dupeMat(material_name):
    mat = bpy.data.materials.get(material_name)
    mat.copy()

#----------------------------------------------------------------------------------    
def applyThisMat(material_name):
    mat = bpy.data.materials.get(material_name)
    all_original_Objects = bpy.context.selected_objects
    
    edit_mode = False
    if (bpy.context.active_object.mode == 'EDIT'):
        edit_mode = True         
    
    for obj in all_original_Objects:
        if obj.type in {'MESH',"CURVE"}:
            bpy.context.view_layer.objects.active = obj
            
            if not edit_mode:
                if len(obj.data.materials)>0 and bpy.context.scene.blitz is True:
                    obj.data.materials.clear()
                    obj.data.materials.append(mat)
                elif len(obj.data.materials)>0 and bpy.context.scene.blitz is False:
                    idx = obj.active_material_index
                    obj.material_slots[idx].material = mat
                elif obj.data.materials:
                    obj.data.materials[0] = mat
                else:
                    obj.data.materials.append(mat)
                    
            if edit_mode:
                stepper = 0
                foundMat = 0
                for slotx in obj.data.materials:
                    if slotx == mat:
                        obj.active_material_index = stepper
                        bpy.ops.object.material_slot_assign()
                        foundMat = 1
                    stepper +=1

                if foundMat == 0:
                    obj.data.materials.append(mat)
                    # now we have to find where it put it
                    stepper = 0
                    for slotx in obj.data.materials:
                        if slotx == mat:
                            obj.active_material_index = stepper
                            bpy.ops.object.material_slot_assign()          
                        stepper +=1
                else:
                    idx = obj.active_material_index
                    obj.material_slots[idx].material = mat



#---------------------------------------------------------------------------------- 
def toLinearRGB(val):
    gamma = ((val + 0.055) / 1.055)**2.4
    scale = val / 12.92
    return np.where (val > 0.04045, gamma, scale)
#---------------------------------------------------------------------------------- 
def RHHextoFloatRGB(hexCode):
    x = (hexCode).lstrip("#")  
    rxRGB= tuple(round(int(x[i:i+2], 16)/255,3) for i in (0, 2, 4))
    tuplefloatRGB = (toLinearRGB(rxRGB[0]),toLinearRGB(rxRGB[1]),toLinearRGB(rxRGB[2]))
    return(tuplefloatRGB)
#---------------------------------------------------------------------------------- 
hxnm = {
    "aliceblue": "#f0f8ff",
    "antiquewhite": "#faebd7",
    "aqua": "#00ffff",
    "aquamarine": "#7fffd4",
    "azure": "#f0ffff",
    "beige": "#f5f5dc",
    "bisque": "#ffe4c4",
    "black": "#000000",
    "blanchedalmond": "#ffebcd",
    "blue": "#0000ff",
    "blueviolet": "#8a2be2",
    "brown": "#a52a2a",
    "burlywood": "#deb887",
    "cadetblue": "#5f9ea0",
    "chartreuse": "#7fff00",
    "chocolate": "#d2691e",
    "coral": "#ff7f50",
    "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc",
    "cosmetic mauve": "#D3BED5",
    "crimson": "#dc143c",
    "cyan": "#00ffff",
    "darkblue": "#00008b",
    "darkcyan": "#008b8b",
    "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9",
    "darkgrey": "#a9a9a9",
    "darkgreen": "#006400",
    "darkkhaki": "#bdb76b",
    "darkmagenta": "#8b008b",
    "darkolivegreen": "#556b2f",
    "darkorange": "#ff8c00",
    "darkorchid": "#9932cc",
    "darkred": "#8b0000",
    "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f",
    "darkslateblue": "#483d8b",
    "darkslategray": "#2f4f4f",
    "darkslategrey": "#2f4f4f",
    "darkturquoise": "#00ced1",
    "darkviolet": "#9400d3",
    "deeppink": "#ff1493",
    "deepskyblue": "#00bfff",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "dodgerblue": "#1e90ff",
    "firebrick": "#b22222",
    "floralwhite": "#fffaf0",
    "forestgreen": "#228b22",
    "fuchsia": "#ff00ff",
    "gainsboro": "#dcdcdc",
    "ghostwhite": "#f8f8ff",
    "gold": "#ffd700",
    "goldenrod": "#daa520",
    "gray": "#808080",
    "grey": "#808080",
    "green": "#008000",
    "greenyellow": "#adff2f",
    "honeydew": "#f0fff0",
    "hotpink": "#ff69b4",
    "indianred": "#cd5c5c",
    "inchworm": "#9C65DF",
    "indigo": "#4b0082",
    "ivory": "#fffff0",
    "japanese blue": "#1C3563",
    "key lime": "#9992F4",
    "khaki": "#f0e68c",
    "lavender": "#e6e6fa",
    "lavenderblush": "#fff0f5",
    "lawngreen": "#7cfc00",
    "lemonchiffon": "#fffacd",
    "lightblue": "#add8e6",
    "lightcoral": "#f08080",
    "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2",
    "lightgray": "#d3d3d3",
    "lightgrey": "#d3d3d3",
    "lightgreen": "#90ee90",
    "lightpink": "#ffb6c1",
    "lightsalmon": "#ffa07a",
    "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa",
    "lightslategray": "#778899",
    "lightslategrey": "#778899",
    "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0",
    "lime": "#00ff00",
    "limegreen": "#32cd32",
    "linen": "#faf0e6",
    "loden purple": "#553A76",
    "magenta": "#ff00ff",
    "maroon": "#800000",
    "mediumaquamarine": "#66cdaa",
    "mediumblue": "#0000cd",
    "mediumorchid": "#ba55d3",
    "mediumpurple": "#9370db",
    "mediumseagreen": "#3cb371",
    "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a",
    "mediumturquoise": "#48d1cc",
    "mediumvioletred": "#c71585",
    "midnightblue": "#191970",
    "mintcream": "#f5fffa",
    "mistyrose": "#ffe4e1",
    "moccasin": "#ffe4b5",
    "navajowhite": "#ffdead",
    "navy": "#000080",
    "oldlace": "#fdf5e6",
    "olive": "#808000",
    "olivedrab": "#6b8e23",
    "orange": "#ffa500",
    "orangered": "#ff4500",
    "orchid": "#da70d6",
    "palegoldenrod": "#eee8aa",
    "palegreen": "#98fb98",
    "paleturquoise": "#afeeee",
    "palevioletred": "#db7093",
    "papayawhip": "#ffefd5",
    "paper bag": "#CEB092",
    "peachpuff": "#ffdab9",
    "peru": "#cd853f",
    "pink": "#ffc0cb",
    "plum": "#dda0dd",
    "powderblue": "#b0e0e6",
    "purple": "#800080",
    "rajah": "#6096EF",
    "red": "#ff0000",
    "rosybrown": "#bc8f8f",
    "royalblue": "#4169e1",
    "saddlebrown": "#8b4513",
    "salmon": "#fa8072",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "seashell": "#fff5ee",
    "sienna": "#a0522d",
    "silver": "#c0c0c0",
    "skyblue": "#87ceeb",
    "slateblue": "#6a5acd",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#fffafa",
    "springgreen": "#00ff7f",
    "steelblue": "#4682b4",
    "tan": "#d2b48c",
    "teal": "#008080",
    "thistle": "#d8bfd8",
    "tomato": "#ff6347",
    "turquoise": "#40e0d0",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "white": "#ffffff",
    "whitesmoke": "#f5f5f5",
    "yellow": "#ffff00",
    "yellowgreen": "#9acd32",
}

def RHNamedRandomColor(allCurrentMats):
    rnColorChoiceName = ""
    x=1
    while x <= len(allCurrentMats):
        rnColorChoice = RHRandomGet()
        rnColorChoiceName = rnColorChoice[0]   
        if rnColorChoiceName not in allCurrentMats and x <= 140:
            rnColorChoiceName = rnColorChoice[0]
            break
        x += 1
    rnColorChoiceValue = RHHextoFloatRGB(rnColorChoice[1])
    return(rnColorChoiceName,rnColorChoiceValue)

def RHRandomGet():
    return (random.choice(list(hxnm.items())))


    