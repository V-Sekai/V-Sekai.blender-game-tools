import bpy
from bpy.types import Scene, PropertyGroup, Panel
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty


# --------------- FUNCTIONS --------------------
# | - Update/Getter/Setter/Items
# ----------------------------------------------


workspace_tab_dict = {
    'ALL': (
        ('SETUP', 'Setup', 'Setup Tab'),
        ('CREATE', 'Rig', 'Create Tab'),
        ('EXPRESSIONS', 'Expressions', 'Expressions Tab'),
        ('BAKE', 'Bake', 'Bake Tab'),
        ('SHAPES', 'ARKit Shapes', 'ARKit Target Shape Keys Settings'),
        ('CONTROL', 'Control', 'Control Rig'),
        ('MOCAP', 'Mocap', 'Motion Capture'),
    ),
    'RIG': (
        ('SETUP', 'Setup', 'Setup Tab'),
        ('CREATE', 'Rig', 'Create Tab'),
        ('EXPRESSIONS', 'Expressions', 'Expressions Tab'),
        ('BAKE', 'Bake', 'Bake Tab'),
    ),
    'MOCAP': (
        ('SETUP', 'Setup', 'Setup Tab'),
        ('SHAPES', 'ARKit Shapes', 'ARKit Target Shape Keys Settings'),
        ('CONTROL', 'Control', 'Control Rig'),
        ('MOCAP', 'Mocap', 'Motion Capture'),
    )
}


def _get_tab_items_from_workspace(self, context):
    return workspace_tab_dict[self.workspace]


def update_tab(self, context):

    if context is None:
        return

    if self.workspace == 'ALL':
        self.all_tab = self.active_tab
    elif self.workspace == 'RIG':
        self.rig_tab = self.active_tab
    elif self.workspace == 'MOCAP':
        self.mocap_tab = self.active_tab

    # if self.active_tab == 'SETUP':
    #     activate_setup_panel()
    # else:
    #     deactivate_setup_panel()


def update_workspace(self, context):

    if self.workspace == 'ALL':
        self.active_tab = self.all_tab
    elif self.workspace == 'RIG':
        self.active_tab = self.rig_tab
    elif self.workspace == 'MOCAP':
        self.active_tab = self.mocap_tab

    # if self.active_tab == 'SETUP':
    #     activate_setup_panel()
    # else:
    #     deactivate_setup_panel()


# def activate_setup_panel():
#     if setup_panel_change_listener not in bpy.app.handlers.depsgraph_update_post:
#         bpy.app.handlers.depsgraph_update_post.append(setup_panel_change_listener)


# def deactivate_setup_panel():
#     if setup_panel_change_listener in bpy.app.handlers.depsgraph_update_post:
#         bpy.app.handlers.depsgraph_update_post.remove(setup_panel_change_listener)

# --------------- CLASSES --------------------
# | - Property Groups (Collection-/PointerProperty)
# ----------------------------------------------

class PinPanels(PropertyGroup):
    # Setup
    FACEIT_PT_SetupRegister: BoolProperty()
    FACEIT_PT_SetupVertexGroups: BoolProperty()
    # Rigging
    FACEIT_PT_Rigging: BoolProperty()
    FACEIT_PT_Landmarks: BoolProperty()
    # Expressoins
    FACEIT_PT_Expressions: BoolProperty()
    FACEIT_PT_ExpressionOptions: BoolProperty()

    # Bake Panel (Utils)
    FACEIT_PT_ShapeKeyUtils: BoolProperty()
    FACEIT_PT_Finalize: BoolProperty()
    FACEIT_PT_RigUtils: BoolProperty()
    FACEIT_PT_Other: BoolProperty()
    FACEIT_PT_ControlRig: BoolProperty()
    # ARKit Shapes
    FACEIT_PT_ArkitTargetShapes: BoolProperty()
    FACEIT_PT_ArkitTargetShapesSetup: BoolProperty()
    # Control Rig
    FACEIT_PT_ControlRigSettings: BoolProperty()
    FACEIT_PT_ControlRigUtils: BoolProperty()
    FACEIT_PT_ControlRigTargetShapes: BoolProperty()
    FACEIT_PT_ControlRigTargetObjects: BoolProperty()
    # Mocap
    FACEIT_PT_MocapSettings: BoolProperty()
    FACEIT_PT_RetargetFBX: BoolProperty()
    FACEIT_PT_MocapFaceCap: BoolProperty()
    FACEIT_PT_MocapEpic: BoolProperty()
    FACEIT_PT_FaceCapText: BoolProperty()
    FACEIT_PT_FaceCapLive: BoolProperty()

    def get_pin(self, panel_idname):
        return getattr(self, panel_idname, 0)


class FaceitWorkspace(PropertyGroup):
    name: StringProperty()
    workspace: EnumProperty(
        name='The Active Faceit Workspace',
        items=(
            ('ALL', 'All', 'Choose this option if you want to have all functionality available.'),
            ('RIG', 'Rig', 'Chosse this option if you only want to create blendshapes. Motion Capture Utils are hidden.'),
            ('MOCAP', 'Mocap', 'Choose this option when your geometry has blendshapes and you only want to do Motion Capture'),
        ),
        default='ALL',
        update=update_workspace,
    )
    active_tab: EnumProperty(
        items=_get_tab_items_from_workspace,
        update=update_tab,
    )

    # Store Value based on workspace
    all_tab: StringProperty(
        default='SETUP'
    )
    rig_tab: StringProperty(
        default='SETUP',
    )
    mocap_tab: StringProperty(
        default='SETUP',
    )

    expand_ui: BoolProperty()


# --------------- REGISTER/UNREGISTER --------------------
# |
# --------------------------------------------------------


def register():

    Scene.faceit_workspace = PointerProperty(
        type=FaceitWorkspace,
    )

    ############## Utilities ##################

    Scene.faceit_shape_key_utils_expand_ui = BoolProperty(
        name='Faceit Utilities',
        default=False
    )
    Scene.faceit_finalize_utils_expand_ui = BoolProperty(
        name='Faceit Utilities',
        default=False
    )
    Scene.faceit_other_utilities_expand_ui = BoolProperty(
        name='Faceit Utilities',
        default=False
    )
    Scene.faceit_expression_options_expand_ui = BoolProperty(
        name='Options',
        default=True
    )
    Scene.faceit_expression_init_expand_ui = BoolProperty(
        name='Initialize',
        default=True
    )

    Scene.faceit_control_rig_expand_ui = BoolProperty(
        default=True
    )

    Scene.faceit_crig_target_shapes_expand_ui = BoolProperty(
        default=True
    )

    Scene.faceit_crig_target_objects_expand_ui = BoolProperty(
        default=True
    )

    Scene.faceit_crig_target_settings_expand_ui = BoolProperty(
        default=True
    )

    Scene.faceit_crig_landmarks_expand_ui = BoolProperty(
        default=False
    )

    Scene.faceit_mocap_general_expand_ui = BoolProperty(
        default=False
    )

    Scene.faceit_mocap_action_expand_ui = BoolProperty(
        default=False
    )

    Scene.faceit_pin_panels = PointerProperty(
        name='Pin Props',
        type=PinPanels,
    )


def unregister():
    # if setup_panel_change_listener in bpy.app.handlers.depsgraph_update_post:
    #     bpy.app.handlers.depsgraph_update_post.remove(setup_panel_change_listener)

    del Scene.faceit_workspace
    del Scene.faceit_other_utilities_expand_ui
    del Scene.faceit_shape_key_utils_expand_ui
    del Scene.faceit_finalize_utils_expand_ui
    del Scene.faceit_control_rig_expand_ui
    del Scene.faceit_crig_landmarks_expand_ui
    del Scene.faceit_mocap_general_expand_ui
    del Scene.faceit_mocap_action_expand_ui
    del Scene.faceit_pin_panels
