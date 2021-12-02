import bpy
from bpy.types import PropertyGroup, Scene
from bpy.props import StringProperty, BoolProperty,  IntProperty, PointerProperty, EnumProperty


# --------------- CLASSES --------------------
# | - Property Groups (Collection-/PointerProperty)
# ----------------------------------------------


# class AmplifyMocapProperties(PropertyGroup):
#     name: String

class Mocap_Motion_Types(PropertyGroup):
    __props = ['blendshapes_target', 'head_target_rotation', 'eye_target_rotation']

    name: StringProperty(
        name='The name of the propertyinstance',
        default='Mocap Target Setup'
    )
    blendshapes_target: BoolProperty(
        name='Shape Keys',
        default=True,
    )
    head_target_rotation: BoolProperty(
        name='Head Rotation',
        default=False
    )
    eye_target_rotation: BoolProperty(
        name='Eye Rotation',
        default=False
    )
    expand: BoolProperty(default=False)

    def read_settings(self):
        ''' Returns all prop values '''
        return [getattr(self, p) for p in self.__props]


class Mocap_Engine_Properties(PropertyGroup):
    filename: StringProperty(
        name='Filename',
        default='',
    )
    # frame_start: IntProperty(
    #     name='Start at Frame',
    #     description='Experimental for negative frames',
    #     default=0,
    # )
    master_expanded: BoolProperty(
        name='Expand UI',
        default=False,
    )
    file_import_expanded: BoolProperty(
        name='Expand UI',
        default=False,
    )
    live_mode_expanded: BoolProperty(
        name='Expanded UI',
        default=False,
    )
    mocap_engine: StringProperty(
        name='Mocap Engine',
        description='The software or app to record or stream motion'
    )
    indices_order: StringProperty(
        name='Order of Shape Key Indices',
        description='The order of the Shape Keys used by this engine'
    )
    # load_to_new_action: BoolProperty(
    #     name='Import to new action',
    #     default=False,
    # )

# --------------- FUNCTIONS --------------------
# | - Update/Getter/Setter
# ----------------------------------------------


def update_record_face_cap(self, context):
    shape_key_set = False
    # if self.MOM_items:
    for item in self.MOM_Items:
        if not shape_key_set:
            if item.osc_address == '/W':
                item.record = self.faceit_record_face_cap
                shape_key_set = True
        elif item.osc_address != '/W':
            item.record = self.faceit_record_face_cap


def mocap_action_poll(self, action):
    return any(['key_block' in fc.data_path for fc in action.fcurves])


def register():
    ############## Mocap General ##################

    Scene.faceit_mocap_action = PointerProperty(
        type=bpy.types.Action,
        name='Active Mocap Action',
        poll=mocap_action_poll
    )
    Scene.faceit_mocap_motion_types = PointerProperty(
        name='Face Cap Settings',
        type=Mocap_Motion_Types
    )

    Scene.faceit_mocap_target_head = StringProperty(
        name='Target Head',
        default=''
    )
    Scene.faceit_mocap_target_eye_l = StringProperty(
        name='Target Eye L',
        default=''
    )
    Scene.faceit_mocap_target_eye_r = StringProperty(
        name='Target Eye R',
        default=''
    )

    ############## Face Cap App ##################

    Scene.faceit_face_cap_mocap_settings = PointerProperty(
        type=Mocap_Engine_Properties,
        name='Face Cap Properties',
    )

    Scene.faceit_record_face_cap = BoolProperty(
        name='Record Face Cap Live Mode',
        update=update_record_face_cap,
        default=False,
        description='Record on Play - Setup AddRoutes first'
    )

    ############## Live Link Face ##################

    Scene.faceit_epic_mocap_settings = PointerProperty(
        type=Mocap_Engine_Properties,
        name='Live Link Face Properties',
    )


def unregister():
    del Scene.faceit_mocap_action
    del Scene.faceit_mocap_motion_types
    del Scene.faceit_mocap_target_head
    del Scene.faceit_mocap_target_eye_l
    del Scene.faceit_mocap_target_eye_r
    del Scene.faceit_face_cap_mocap_settings
    del Scene.faceit_record_face_cap
    del Scene.faceit_epic_mocap_settings
