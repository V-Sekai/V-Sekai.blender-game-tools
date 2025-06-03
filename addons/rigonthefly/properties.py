#########################################
#######       Rig On The Fly      #######
####### Copyright © 2021 Dypsloom #######
#######    https://dypsloom.com/  #######
#########################################

from locale import normalize
import bpy
from .panels import dynamics

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
    
    Scene.rotf_no_bake_on_remove = BoolProperty(
        name="no bake on remove",
        description="When checked ON, does not bake motion when removing a Rig on the Fly constraint", 
        default=False
    )

    Scene.rotf_bake_on_load = BoolProperty(
        name="bake on load", 
        description="When checked ON, bakes and removes RotF bones before loading a rig state", 
        default=False
        )
    
    #----------------------------------------------------------------------------------------
    Scene.rotf_mirror_controller_size = BoolProperty(
        name="mirror size", 
        description="mirrors the controllers' size", 
        default=True
        )
    
    Scene.rotf_controller_shape_thickness = FloatProperty(
        name="Shape Thickness",
        description="Thickness of the controller shapes",
        default=3.0,
        min=0.1,
        update=shapeThickness
        )
    #----------------------------------------------------------------------------------------
    Scene.rotf_orient_mirror = BoolProperty(
        name="orient mirror", 
        description="mirrors the oriented controllers", 
        default=True
        )
    #----------------------------------------------------------------------------------------
    Scene.rotf_rotation_distribution_chain_length = IntProperty(
        name="",
        description="Length of rotation distribution chain",
        default=2,
        min=2
        )
    #----------------------------------------------------------------------------------------
    Scene.rotf_bend_ik_chain_length = IntProperty(
        name="",
        description="Length of the ik chain",
        default=2,
        min=2
        )

    Scene.rotf_bend_ik_pole_vector = BoolProperty(
        name="pole vector", 
        description="Adds a pole vector control for IK", 
        default=True
        )

    Scene.rotf_bend_ik_default_pole_axis = EnumProperty(
        name="",
        description="Axis used for setting the Pole Vector if Limb is Straight does not work if the Y axis is not pointing down the chain",
        items=[
            ('+X', "+X", "", 1),
            ('-X', "- X", "", 2),
            #('+Y', "+Y", "", 3),
            #('-Y', "- Y", "", 4),
            ('+Z', "+Z", "", 3),
            ('-Z', "- Z", "", 4)
            ]
        )
    
    Scene.rotf_bend_ik_stretch_type = EnumProperty(
        name="",
        description="Type of stretching when using IK",
        items=[
            ('None', "None", "", 1),
            ('Location', "Location", "", 2),
            ('Scale', "Scale", "", 3)
            ]
        )
    #----------------------------------------------------------------------------------------
    Scene.rotf_stretch_ik_chain_length = IntProperty(
        name="",
        description="Length of the ik Stretch chain",
        default=2,
        min=2
        )
    
    Scene.rotf_stretch_ik_stretch_type = EnumProperty(
        name="",
        description="Type of stretching when using IK",
        items=[
            ('Location', "Location", "", 1),
            ('Scale', "Scale", "", 2),
            ('Keep Volume', "Keep Volume", "", 3)
            ]
        )

    Scene.rotf_stretch_ik_distribute_rotation = BoolProperty(
        name="distribute rotation", 
        description="Distributes rotation along the chain", 
        default=True
        )
    #----------------------------------------------------------------------------------------
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
    
    Scene.rotf_aim_distance = FloatProperty(
        name="",
        description="Distance between the Aiming Bone and the Aim Target on creation",
        default=1.00,
        min=0.0001
        )
    #----------------------------------------------------------------------------------------
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

    #----------------------------------------------------------------------------------------
    Scene.rotf_frame_range_step = IntProperty(
        name="step",
        description="Space between each frame added by Key Range",
        default=1,
        min=1
        )
    
    Scene.rotf_frame_range_start = IntProperty(
        name="start",
        description="Start frame to be keyed by Key Range",
        default=1,
        update=frameRangeStartUpdate
        )
    
    Scene.rotf_frame_range_end = IntProperty(
        name="end",
        description="End frame to be keyed by Key Range",
        default=10,
        update=frameRangeEndUpdate
        )
    
    Scene.rotf_key_available = BoolProperty(
        name="available", 
        description="When checked ON, key range adds key only to keyed transform channels", 
        default=False
        )

    Scene.rotf_key_location = BoolProperty(
        name="location", 
        description="When checked ON, key range adds key to location", 
        default=True
        )

    Scene.rotf_key_rotation = BoolProperty(
        name="rotation", 
        description="When checked ON, key range adds key to rotation", 
        default=True
        )

    Scene.rotf_key_scale = BoolProperty(
        name="scale", 
        description="When checked ON, key range adds key to scale", 
        default=True
        )

    Scene.rotf_selected_keys = BoolProperty(
        name="selected keys", 
        description="When checked ON, use the selected keys only of the active controller", 
        default=False
        )

    Scene.rotf_offset_keys_factor = FloatProperty(
        name="offset amount",
        description="Value used to offset keys of the selected controllers along the timeline",
        default=1.0,
        )

    #----------------------------------------------------------------------------------------
    Scene.rotf_dynamics_start = IntProperty(
        name="start",
        description="Start frame to be keyed by Inertia On Transforms",
        default=1,
        update=dynamicsOnTransformsStartUpdate
        )
    
    Scene.rotf_dynamics_end = IntProperty(
        name="end",
        description="End frame to be keyed by Inertia On Transforms",
        default=100,
        update=dynamicsOnTransformsEndUpdate
        )

    Scene.rotf_blend_frame = IntProperty(
        name="blend frame",
        description="frame at which the dynamics starts to get blended into the original motion",
        default=50,
        update=dynamicsOnTransformsBlendUpdate
        )

    Scene.rotf_frequency = FloatProperty(
        name="frequency",
        description="reaction speed to change in motion",
        default=1,
        min=0.00001,
        update=dynamics.dynamicsCurveUpdate
        )
    
    Scene.rotf_damping = FloatProperty(
        name="damping",
        description="how much the motion settles",
        default=1,
        min=0,
        update=dynamics.dynamicsCurveUpdate
        )
    
    Scene.rotf_response = FloatProperty(
        name="response",
        description="initial response to change in motion",
        default=0,
        update=dynamics.dynamicsCurveUpdate
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

    Object.rotf_sfp_nla_state = CollectionProperty(
        type=NLAState
        )
    
    Object.rotf_copy_of_proxy = PointerProperty(
        type=bpy.types.Object
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

#Properties Update Functions
def shapeThickness(self, context):
    scene = context.scene
    for obj in bpy.data.collections['RotF_ControllerShapes'].objects:
        obj.modifiers["RotF_Wireframe_Thickness"].node_group = bpy.data.node_groups["RotF_Wireframe_Thickness"]
    bpy.data.node_groups["RotF_Wireframe_Thickness"].nodes["Value"].outputs[0].default_value = scene.rotf_controller_shape_thickness

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

def dynamicsOnTransformsStartUpdate(self, context):
    scene = context.scene
    if scene == None:
        return
    if scene.rotf_dynamics_start > scene.rotf_dynamics_end:
        scene.rotf_dynamics_end = scene.rotf_dynamics_start + 1
    if scene.rotf_dynamics_start > scene.rotf_blend_frame:
        scene.rotf_blend_frame = scene.rotf_dynamics_start
    
    dynamics.dynamicsCurveUpdate(self, context)

def dynamicsOnTransformsEndUpdate(self, context):
    scene = context.scene
    if scene == None:
        return
    if scene.rotf_dynamics_start > scene.rotf_dynamics_end:
        scene.rotf_dynamics_start = scene.rotf_dynamics_end - 1

    if scene.rotf_blend_frame > scene.rotf_dynamics_end:
        scene.rotf_blend_frame = scene.rotf_dynamics_end - 1 
    
    dynamics.dynamicsCurveUpdate(self, context)

def dynamicsOnTransformsBlendUpdate(self, context):
    scene = context.scene
    if scene == None:
        return
    if scene.rotf_dynamics_start > scene.rotf_blend_frame:
        scene.rotf_blend_frame = scene.rotf_dynamics_start
    if scene.rotf_blend_frame > scene.rotf_dynamics_end:
        scene.rotf_blend_frame = scene.rotf_dynamics_end - 1

    dynamics.dynamicsCurveUpdate(self, context)


    

