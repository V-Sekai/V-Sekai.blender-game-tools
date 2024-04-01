from bpy.props import (BoolProperty, EnumProperty, PointerProperty,
                       StringProperty)
from bpy.types import PropertyGroup, Scene

workspace_tab_dict = {
    'ALL': (
        ('SETUP', 'Setup', 'Setup Tab'),
        ('CREATE', 'Rig', 'Create Tab'),
        ('EXPRESSIONS', 'Expressions', 'Expressions Tab'),
        ('BAKE', 'Bake', 'Bake Tab'),
        ('SHAPES', 'Shapes', 'Target Shape Keys Settings'),
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
        ('SHAPES', 'Shapes', 'Target Shape Keys Settings'),
        ('CONTROL', 'Control', 'Control Rig'),
        ('MOCAP', 'Mocap', 'Motion Capture'),
    )
}


def _get_tab_items_from_workspace(self, context):
    workspaces = workspace_tab_dict[self.workspace]
    if context.scene.faceit_use_existing_armature:
        # remove the create tab
        workspaces = [w for w in workspaces if w[0] != 'CREATE']
    return workspaces


def update_tab(self, context):
    if context is None:
        return
    if self.workspace == 'ALL':
        self.all_tab = self.active_tab
    elif self.workspace == 'RIG':
        self.rig_tab = self.active_tab
    elif self.workspace == 'MOCAP':
        self.mocap_tab = self.active_tab


def update_workspace(self, context):
    if self.workspace == 'ALL':
        self.active_tab = self.all_tab
    elif self.workspace == 'RIG':
        self.active_tab = self.rig_tab
    elif self.workspace == 'MOCAP':
        self.active_tab = self.mocap_tab


class PinPanels(PropertyGroup):
    # Setup
    FACEIT_PT_SetupRegister: BoolProperty()
    FACEIT_PT_SetupVertexGroups: BoolProperty()
    FACEIT_PT_BodyRigSetup: BoolProperty()
    # Rigging
    FACEIT_PT_Rigging: BoolProperty()
    FACEIT_PT_Landmarks: BoolProperty()
    # Expressoins
    FACEIT_PT_Expressions: BoolProperty()
    FACEIT_PT_ExpressionOptions: BoolProperty()
    # Bake Panel (Utils)
    FACEIT_PT_BakeExpressions: BoolProperty()
    FACEIT_PT_ShapeKeyUtils: BoolProperty()
    FACEIT_PT_RigUtils: BoolProperty()
    FACEIT_PT_Other: BoolProperty()
    # ARKit Shapes
    FACEIT_PT_TargetShapeLists: BoolProperty()
    FACEIT_PT_RetargetShapesSetup: BoolProperty()
    # Control Rig
    FACEIT_PT_ControlRig: BoolProperty()
    FACEIT_PT_ControlRigSettings: BoolProperty()
    FACEIT_PT_ControlRigAnimation: BoolProperty()
    FACEIT_PT_ControlRigUtils: BoolProperty()
    FACEIT_PT_ControlRigTargetShapes: BoolProperty()
    FACEIT_PT_ControlRigTargetObjects: BoolProperty()
    # Mocap
    FACEIT_PT_MocapUtils: BoolProperty()
    FACEIT_PT_MocapImporters: BoolProperty()
    FACEIT_PT_MocapLive: BoolProperty()
    FACEIT_PT_MocapSetup: BoolProperty()
    FACEIT_PT_RetargetFBX: BoolProperty()

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
    all_tab: StringProperty(
        default='SETUP',
        description='The active tab when the ALL workspace.'
    )
    rig_tab: StringProperty(
        default='SETUP',
        description='The active tab when the RIG workspace.'
    )
    mocap_tab: StringProperty(
        default='SETUP',
        description='The active tab in the MOCAP Workspace',
    )
    expand_ui: BoolProperty()


# --------------- REGISTER/UNREGISTER --------------------
# |
# --------------------------------------------------------


def register():

    Scene.faceit_workspace = PointerProperty(
        type=FaceitWorkspace,
    )
    Scene.faceit_expression_init_expand_ui = BoolProperty(
        name='Initialize',
        default=True
    )
    Scene.faceit_pin_panels = PointerProperty(
        name='Pin Props',
        type=PinPanels,
    )


def unregister():
    del Scene.faceit_workspace
    del Scene.faceit_expression_init_expand_ui
    del Scene.faceit_pin_panels
