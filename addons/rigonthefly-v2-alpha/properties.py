#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

import bpy

from bpy.types import Scene, Object, PoseBone, Bone
from bpy.props import IntProperty, StringProperty, EnumProperty, BoolProperty, FloatProperty, CollectionProperty, PointerProperty
from .core import rigState
from .panels import keyframeTools

def register():

    #scene properties
    Scene.rotf_folder_name = StringProperty(
        name="folder name",
        default='None'
        )
   
    Scene.rotf_folder_path = StringProperty(
        default=''
        )

    Scene.rotf_state_collection = CollectionProperty(
        type=RigStateFilePaths
        )

    Scene.rotf_smart_frames = BoolProperty(
        name="smart frames", 
        description="When checked ON, bakes only on frames where there are keys", 
        default=False
        )
    
    Scene.rotf_smart_channels = BoolProperty(
        name="smart channels", 
        description="When checked ON, bakes only the relevant transfrom channels", 
        default=False
        )

    Scene.rotf_bake_on_load = BoolProperty(
        name="bake on load", 
        description="When checked ON, bakes and removes RotF bones before loading a rig state", 
        default=False
        )

    Scene.rotf_frame_range_step = IntProperty(
        name="",
        description="Space between each frame added by Key Range",
        default=1,
        min=1
        )
    
    Scene.rotf_frame_range_start = IntProperty(
        name="",
        description="Start frame to be keyed by Key Range",
        default=1,
        update=frameRangeStartUpdate
        )
    
    Scene.rotf_frame_range_end = IntProperty(
        name="",
        description="End frame to be keyed by Key Range",
        default=10,
        update=frameRangeEndUpdate
        )

    Scene.rotf_ik_chain_length = IntProperty(
        name="",
        description="Length of the ik chain",
        default=2,
        min=2
        )

    Scene.rotf_ikScaleStretch = BoolProperty(
        name="ik scale stretch", 
        description="Enables stretching with scale for IK", 
        default=False
        )
    
    Scene.rotf_ikLocationStretch = BoolProperty(
        name="ik location stretch", 
        description="Enables stretching with only translations for IK", 
        default=False
        )

    Scene.rotf_pole_vector = BoolProperty(
        name="pole vector", 
        description="Adds a pole vector control for IK", 
        default=True
        )

    Scene.rotf_rotation_distribution_chain_length = IntProperty(
        name="",
        description="Length of rotation distribution chain",
        default=2,
        min=2
        )

    Scene.rotf_ik_default_pole_axis = EnumProperty(
        name="",
        description="Axis used for setting the Pole Vector if Limb is Straight",
        items=[
            ('+X', "+X", "", 1),
            ('-X', "- X", "", 2),
            ('+Z', "+Z", "", 3),
            ('-Z', "- Z", "", 4)
            ]
        )
    
    Scene.rotf_ik_stretch = EnumProperty(
        name="",
        description="Type of stretching when using IK",
        items=[
            ('None', "None", "", 1),
            ('Location', "Location", "", 2),
            ('Scale', "Scale", "", 3)
            ]
        )

    Scene.rotf_aim_stretch = BoolProperty(
        name="aim stretch", 
        description="Enables stretching", 
        default=False
        )

    Scene.rotf_aim_axis = EnumProperty(
        name="",
        description="Axis used to Aim",
        items=[
            ('X', "+X", "", 1),
            ('-X', "- X", "", 2),
            ('Y', "+Y", "", 3),
            ('-Y', "- Y", "", 4),
            ('Z', "+Z", "", 5),
            ('-Z', "- Z", "", 6)
            ]
        )

    Scene.rotf_simple_copy_location = BoolProperty(
        name="copy location", 
        description="include location when adding copy transform", 
        default=False
        )

    Scene.rotf_simple_copy_rotation = BoolProperty(
        name="copy rotation", 
        description="include rotation when adding copy transform", 
        default=False
        )
    
    Scene.rotf_simple_copy_scale = BoolProperty(
        name="copy scale", 
        description="include scale when adding copy transform", 
        default=False
        )

    Scene.rotf_aim_distance = FloatProperty(
        name="",
        description="Distance between the Aiming Bone and the Aim Target on creation",
        default=1.00,
        min=0.0001
        )
    
    Scene.rotf_simple_aim_axis = EnumProperty(
        name="",
        description="Axis used to Aim",
        items=[
            ('X', "+X", "", 1),
            ('-X', "- X", "", 2),
            ('Y', "+Y", "", 3),
            ('-Y', "- Y", "", 4),
            ('Z', "+Z", "", 5),
            ('-Z', "- Z", "", 6)
            ]
        )

    Scene.rotf_simple_influence = FloatProperty(
        name="Influence",
        description="Influence value given to the simple constraints",
        default=1.00,
        min=0.0,
        max=1.0
        )

    #custom shapes properties
    Scene.rotf_base_customShape = PointerProperty(
        type=bpy.types.Object
        )

    Scene.rotf_orient_customShape = PointerProperty(
        type=bpy.types.Object
        )

    Scene.rotf_proxy_customShape = PointerProperty(
        type=bpy.types.Object
        )

    Scene.rotf_rootMotion_customShape = PointerProperty(
        type=bpy.types.Object
        )
    
    Scene.rotf_extraBone_customShape = PointerProperty(
        type=bpy.types.Object
        )

    Scene.rotf_centerOfMass_customShape = PointerProperty(
        type=bpy.types.Object
        )

    Scene.rotf_rotationDistribution_customShape = PointerProperty(
        type=bpy.types.Object
        )  

    Scene.rotf_ikTarget_customShape = PointerProperty(
        type=bpy.types.Object
        )
    
    Scene.rotf_poleVector_customShape = PointerProperty(
        type=bpy.types.Object
        )

    Scene.rotf_worldSpace_customShape = PointerProperty(
        type=bpy.types.Object
    )

    Scene.rotf_aimSpace_customShape = PointerProperty(
        type=bpy.types.Object
    )

    Scene.rotf_aimTarget_customShape = PointerProperty(
        type=bpy.types.Object
    )

    Scene.rotf_parentSpace_customShape = PointerProperty(
        type=bpy.types.Object
    )

    Scene.rotf_reverseHierarchySpace_customShape = PointerProperty(
        type=bpy.types.Object
    )

    #object properties      
    Object.rotf_rig_states_manager = rigState.RigStatesManager()
    
    Object.rotf_rig_state = CollectionProperty(
        type=Constraint
        )
    
    Object.rotf_sfp_rig_state = StringProperty(
        default=''
        )
        #CollectionProperty(
        #type=Constraint
        #)

    Object.rotf_sfp_nla_state = CollectionProperty(
        type=NLAState
        )

    #bone properties
    Bone.rotf_pointer_list = CollectionProperty(
        name="pointer list",
        type=BonePointer
        )
    
    Bone.is_rotf = BoolProperty(
        name="is Rig on the Fly", 
        description="Is a bone made by Rig on the Fly", 
        default=False
        )
    
    #pose bone properties
    PoseBone.rotf_previous_shape = PointerProperty(
        type=bpy.types.Object
        )

# bpy.rotf_pose_bone_selection will store bone in order of selection
bpy.rotf_pose_bone_selection = []

class RigStateFilePaths(bpy.types.PropertyGroup):
    filename : bpy.props.StringProperty()

class BonePointer(bpy.types.PropertyGroup):
    armature_object : bpy.props.PointerProperty(type=bpy.types.Object)
    bone_name : bpy.props.StringProperty()

class BoneProperty(bpy.types.PropertyGroup):
    name : bpy.props.StringProperty()

class BoolPropertyGroup(bpy.types.PropertyGroup):
    value : bpy.props.BoolProperty()

class StringPropertyGroup(bpy.types.PropertyGroup):
    string : bpy.props.StringProperty()

class IntPropertyGroup(bpy.types.PropertyGroup):
    int : bpy.props.IntProperty()

class FloatPropertyGroup(bpy.types.PropertyGroup):
    float : bpy.props.FloatProperty()

class Constraint(bpy.types.PropertyGroup):
    full_name : bpy.props.StringProperty()
    constraint_type : bpy.props.StringProperty()
    bone_list : CollectionProperty(type=BoneProperty)
    bool_list : CollectionProperty(type=BoolPropertyGroup)
    string_list : CollectionProperty(type=StringPropertyGroup)
    int_list : CollectionProperty(type=IntPropertyGroup)
    float_list : CollectionProperty(type=FloatPropertyGroup)

class NLAState(bpy.types.PropertyGroup):
    action_name : bpy.props.StringProperty()
    action_extrapolation : bpy.props.StringProperty()
    action_blend_type : bpy.props.StringProperty()
    action_influence : bpy.props.FloatProperty()
    nla_tracks_mute : bpy.props.StringProperty()

def frameRangeStartUpdate(self, context):
    scene = context.scene
    if scene == None:
        return
    if scene.rotf_frame_range_start > scene.rotf_frame_range_end:
        scene.rotf_frame_range_end = scene.rotf_frame_range_start

def frameRangeEndUpdate(self, context):
    scene = context.scene
    if scene == None:
        return
    if scene.rotf_frame_range_start > scene.rotf_frame_range_end:
        scene.rotf_frame_range_start = scene.rotf_frame_range_end