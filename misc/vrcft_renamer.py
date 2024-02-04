import bpy

bl_info = {
    "name": "VRCFaceTracking Renamer",
    "blender": (3, 0, 0),
    "category": "Object",
}

SRanipal = [
"Eye_Left_Blink",
"Eye_Right_Blink",
"Eye_Left_Left",
"Eye_Left_Right",
"Eye_Left_Up",
"Eye_Left_Down",
"Eye_Right_Right",
"Eye_Right_Left",
"Eye_Right_Up",
"Eye_Right_Down",
"Eye_Left_Wide",
"Eye_Right_Wide",
"Eye_Left_squeeze",
"Eye_Right_squeeze",
"Eye_Left_Dilation",
"Eye_Right_Dilation",
"Eye_Right_Constrict",
"Eye_Left_Constrict",
"Eye_Left_squeeze",
"Eye_Left_squeeze",
"Eye_Right_squeeze",
"Eye_Right_squeeze",
"Eye_Left_Wide",
"Eye_Right_Wide",
"Eye_Left_Wide",
"Eye_Right_Wide",
"Mouth_Smile_Left",
"Mouth_Smile_Right",
"Cheek_Puff_Left",
"Cheek_Puff_Right",
"Mouth_Smile_Left",
"Mouth_Smile_Right",
"Cheek_Suck",
"Cheek_Suck",
"Mouth_Upper_Inside",
"Mouth_Upper_Inside",
"Mouth_Lower_Inside",
"Mouth_Lower_Inside",
"Jaw_Open",
"Jaw_Left",
"Jaw_Right",
"Jaw_Forward",
"Mouth_Upper_Overturn",
"Mouth_Upper_Overturn",
"Mouth_Lower_Overturn",
"Mouth_Lower_Overturn",
"Mouth_Pout",
"Mouth_Pout",
"Mouth_Ape_Shape",
"Mouth_Ape_Shape",
"Mouth_Ape_Shape",
"Mouth_Ape_Shape",
"",
"Mouth_Upper_Left",
"Mouth_Lower_Left",
"Mouth_Upper_Right",
"Mouth_Lower_Right",
"Mouth_Smile_Left",
"Mouth_Smile_Right",
"Mouth_Sad_Left",
"Mouth_Sad_Right",
"Mouth_Smile_Left",
"Mouth_Smile_Right",
"Mouth_Lower_Overlay",
"Mouth_Lower_Overlay",
"Mouth_O_Shape",
"Mouth_Lower_Overlay",
"Mouth_Upper_UpLeft",
"Mouth_Upper_UpRight",
"Mouth_Lower_DownLeft",
"Mouth_Lower_DownRight",
"",
"",
"",
"",
"Mouth_Sad_Left",
"Mouth_Sad_Right",
"Tongue_LongStep1",
"Tongue_LongStep2",
"Tongue_Down",
"Tongue_Up",
"Tongue_Left",
"Tongue_Right",
"Tongue_UpLeft_Morph",
"Tongue_UpRight_Morph",
"Tongue_DownLeft_Morph",
"Tongue_DownRight_Morph",
"Tongue_Roll",
]
 
ARkit = [
"eyeBlinkLeft",
"eyeBlinkRight",
"eyeLookOutLeft",
"eyeLookInLeft",
"eyeLookUpLeft",
"eyeLookDownLeft",
"eyeLookOutRight",
"eyeLookInRight",
"eyeLookUpRight",
"eyeLookDownRight",
"eyeWideLeft",
"eyeWideRight",
"eyeSquintLeft",
"eyeSquintRight",
"",
"",
"",
"",
"browDownLeft",
"browDownLeft",
"browDownRight",
"browDownRight",
"browInnerUp",
"browInnerUp",
"browOuterUpLeft",
"browOuterUpRight",
"cheekSquintLeft",
"cheekSquintRight",
"cheekPuff",
"cheekPuff",
"noseSneerLeft",
"noseSneerRight",
"",
"",
"mouthRollUpper",
"mouthRollUpper",
"mouthRollLower",
"mouthRollLower",
"jawOpen",
"jawLeft",
"jawRight",
"jawForward",
"mouthFunnel",
"mouthFunnel",
"mouthFunnel",
"mouthFunnel",
"mouthPucker",
"mouthPucker",
"mouthClose",
"mouthClose",
"mouthClose",
"mouthClose",
"mouthClose",
"mouthLeft",
"mouthLeft",
"mouthRight",
"mouthRight",
"mouthSmileLeft",
"mouthSmileRight",
"mouthFrownLeft",
"mouthFrownRight",
"mouthDimpleLeft",
"mouthDimpleRight",
"mouthShrugUpper",
"mouthShrugLower",
"mouthFunnel",
"mouthShrugLower",
"mouthUpperUpLeft",
"mouthUpperUpRight",
"mouthLowerDownLeft",
"mouthLowerDownRight",
"mouthPressLeft",
"mouthPressRight",
"mouthPressLeft",
"mouthPressRight",
"mouthStretchLeft",
"mouthStretchRight",
"tongueOut",
"tongueOut",
"",
"",
"",
"",
"",
"",
"",
"",
""
]

FACS = [
"Eyes_Closed_L",
"Eyes_Closed_L",
"Eyes_Look_Left_L",
"Eyes_Look_Right_L",
"Eyes_Look_Up_L",
"Eyes_Look_Down_L",
"Eyes_Look_Right_R",
"Eyes_Look_Left_R",
"Eyes_Look_Up_R",
"Eyes_Look_Down_R",
"Upper_Lid_Raiser_L",
"Upper_Lid_Raiser_R",
"Lid_Tightener_L",
"Lid_Tightener_R",
"",
"",
"",
"",
"Brow_Lowerer_L",
"Brow_Lowerer_L",
"Brow_Lowerer_R",
"Brow_Lowerer_R",
"Inner_Brow_Raiser_L",
"Inner_Brow_Raiser_R",
"Outer_Brow_Raiser_L",
"Outer_Brow_Raiser_R",
"Cheek_Raiser_L",
"Cheek_Raiser_R",
"Cheek_Puff_L",
"Cheek_Puff_R",
"Nose_Wrinkler_L",
"Nose_Wrinkler_R",
"Cheek_Suck_L",
"Cheek_Suck_R",
"Lip_Suck_RT",
"Lip_Suck_LT",
"Lip_Suck_RB",
"Lip_Suck_LB",
"Jaw_Drop",
"Jaw_Sideways_Left",
"Jaw_Sideways_Right",
"Jaw_Thrust",
"Lip_Funneler_RT",
"Lip_Funneler_LT",
"Lip_Funneler_RB",
"Lip_Funneler_LB",
"Lip_Pucker_L",
"Lip_Pucker_R",
"Lip_Towards_LB",
"Lip_Towards_LT",
"Lip_Towards_RB",
"Lip_Towards_RT",
"Lip_Towards",
"Mouth_Left",
"Mouth_Left",
"Mouth_Right",
"Mouth_Right",
"Lip_Corner_Puller_L",
"Lip_Corner_Puller_R",
"Lip_Corner_Depressor_L",
"Lip_Corner_Depressor_R",
"Dimpler_L",
"Dimpler_R",
"Chin_Raiser_B",
"Chin_Raiser_T",
"Lip_Funneler",
"Chin_Raiser_B",
"Upper_Lip_Raiser_L",
"Upper_Lip_Raiser_R",
"Lower_Lip_Depressor_L",
"Lower_Lip_Depressor_R",
"Lip_Pressor_L",
"Lip_Pressor_R",
"Lip_Tightener_L",
"Lip_Tightener_R",
"Lip_Stretcher_L",
"Lip_Stretcher_R",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
""
]

UnifiedExpressions = [
"EyeClosedLeft",
"EyeClosedRight",
"EyeLookOutLeft",
"EyeLookInLeft",
"EyeLookUpLeft",
"EyeLookDownLeft",
"EyeLookOutRight",
"EyeLookInRight",
"EyeLookUpRight",
"EyeLookDownRight",
"EyeWideLeft",
"EyeWideRight",
"EyeSquintLeft",
"EyeSquintRight",
"EyeDilationLeft",
"EyeDilationRight",
"EyeConstrictLeft",
"EyeConstrictRight",
"BrowInnerDownLeft",
"BrowOuterDownLeft",
"BrowInnerDownRight",
"BrowOuterDownRight",
"BrowInnerUpLeft",
"BrowInnerUpRight",
"BrowOuterUpLeft",
"BrowOuterUpRight",
"CheekSquintLeft",
"CheekSquintRight",
"CheekPuffLeft",
"CheekPuffRight",
"NoseSneerLeft",
"NoseSneerRight",
"CheekSuckLeft",
"CheekSuckRight",
"LipSuckUpperRight",
"LipSuckUpperLeft",
"LipSuckLowerRight",
"LipSuckLowerLeft",
"JawOpen",
"JawLeft",
"JawRight",
"JawForward",
"LipFunnelUpperRight",
"LipFunnelUpperLeft",
"LipFunnelLowerRight",
"LipFunnelLowerLeft",
"LipPuckerLeft",
"LipPuckerRight",
"MouthApeShape",
"MouthApeShape",
"MouthApeShape",
"MouthApeShape",
"MouthClose",
"MouthUpperLeft",
"MouthLowerLeft",
"MouthUpperRight",
"MouthLowerRight",
"MouthSmileLeft",
"MouthSmileRight",
"MouthFrownLeft",
"MouthFrownRight",
"MouthDimpleLeft",
"MouthDimpleRight",
"MouthRaiserUpper",
"MouthRaiserLower",
"",
"MouthShrugLower",
"MouthUpperUpLeft",
"MouthUpperUpRight",
"MouthLowerDownLeft",
"MouthLowerDownRight",
"MouthPressLeft",
"MouthPressRight",
"MouthTightenerLeft",
"MouthTightenerRight",
"MouthStretchLeft",
"MouthStretchRight",
"TongueOut",
"TongueOut",
"TongueDown",
"TongueUp",
"TongueLeft",
"TongueRight",
"",
"",
"",
"",
"TongueRoll"
]
 
ExpressionsDict = {
    'SRANIPAL' : SRanipal,
    'ARKIT' : ARkit,
    'FACS' : FACS,
    'UNIFIEDEXPRESSIONS' : UnifiedExpressions
}

# Define the panel class
class MyPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_my_panel"
    bl_label = "VRCFaceTracking Shapekey Renamer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRCFT Shapekey Renamer"

    def draw(self, context):
        layout = self.layout
        # Add UI elements to the panel here
        ob = context.object
        
        row = layout.row()
        row.label(text="Original format:")
        row = layout.row()
        row.prop(ob, "globalOriginal", expand=True)
        
        row = layout.row()
        row.label(text="Target format:")
        row = layout.row()
        row.prop(ob, "globalTarget", expand=True)
        
        layout.operator(OBJECT_OT_rename_shapekeys.bl_idname)

# Define the operator class for the shapekey renaming tool
class OBJECT_OT_rename_shapekeys(bpy.types.Operator):
    bl_idname = "object.rename_shapekeys"
    bl_label = "Rename Shapekeys"
    
    my_enum: bpy.props.EnumProperty(
        items=(
            ('SRANIPAL', "SRanipal", ""),
            ('ARKIT', "ARkit", ""),
            ('FACS', "FACS", ""),
            ('UNIFIEDEXPRESSIONS', "Unified Expressions", "")
        ),
        default='SRANIPAL'
    )

    def execute(self, context):
        # Get the active object
        obj = context.active_object

        # Get the shapekeys of the object
        try:
            shapekeys = obj.data.shape_keys.key_blocks
        except AttributeError:
            # Will be raised if there are no shapekeys
            return {'ERROR'}

        # If the two formats are the same, fly
        if (bpy.context.object.globalOriginal == bpy.context.object.globalTarget):
            return {'CANCELLED'}

        # Create a dictionary that maps the original shapekey names to the target shapekey names
        name_map = dict(zip(
            ExpressionsDict[bpy.context.object.globalOriginal], 
            ExpressionsDict[bpy.context.object.globalTarget]))
            
        # Rename the shapekeys using the name_map dictionary
        for shapekey in shapekeys:
            if shapekey.name in name_map and name_map[shapekey.name]: # check for empty string
                shapekey.name = name_map[shapekey.name]

        return {'FINISHED'}

# Register the panel and operator classes
def register():
    bpy.utils.register_class(MyPanel)
    bpy.utils.register_class(OBJECT_OT_rename_shapekeys)
    
    bpy.types.Object.globalOriginal = bpy.props.EnumProperty(
        items=(
            ('SRANIPAL', "SRanipal", ""),
            ('ARKIT', "ARkit", ""),
            ('FACS', "FACS", ""),
            ('UNIFIEDEXPRESSIONS', "Unified Expressions", "")
        ),
        default='SRANIPAL'
    )
    
    bpy.types.Object.globalTarget = bpy.props.EnumProperty(
        items=(
            ('SRANIPAL', "SRanipal", ""),
            ('ARKIT', "ARkit", ""),
            ('FACS', "FACS", ""),
            ('UNIFIEDEXPRESSIONS', "Unified Expressions", "")
        ),
        default='UNIFIEDEXPRESSIONS'
    )


# Unregister the panel and operator classes
def unregister():
    bpy.utils.unregister_class(MyPanel)
    bpy.utils.unregister_class(OBJECT_OT_rename_shapekeys)
    del bpy.types.Object.my_global_enum

# Test the addon by registering and unregistering the panel and operator classes
if __name__ == "__main__":
    register()
    #unregister()
