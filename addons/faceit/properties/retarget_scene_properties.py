import bpy
from bpy.types import Scene, PropertyGroup
from bpy.props import CollectionProperty, FloatProperty, IntProperty, BoolProperty, EnumProperty, StringProperty

# --------------- CLASSES --------------------
# | - Property Groups (Collection-/PointerProperty)
# ----------------------------------------------


class TargetShapes(PropertyGroup):
    name: StringProperty(
        name='Target Shape',
        description='The Target Shape',
        default='---',
    )
    index: IntProperty(
        name='The Index from target shape item',
        default=0
    )
    parent_idx: IntProperty(
        name='The Index from parent shape item'
    )


class Retarget_Shapes(PropertyGroup):

    name: StringProperty(
        name='ARKit Expression',
        description='The ARKit Expression Name (Source Shape)',
        options=set(),
    )
    display_name: StringProperty(
        name='ARKit Expression',
        description='The ARKit Expression Display Name (Source Shape)',
        options=set(),

    )
    index: IntProperty(
        options=set(),

    )
    # frame: IntProperty()
    # current_driver_data_path: StringProperty()
    use_animation: BoolProperty(
        name='Use Animation',
        description='If this is False, the specified expression won\'t be animated by Faceit operators.',
        default=True,
        options=set()  # {'LIBRARY_EDITABLE'}
    )
    target_list_index: IntProperty(
        name='Target Shape Index',
        default=0,
        description='Index of Active Target Shape',
        options=set(),
    )
    target_shapes: CollectionProperty(
        name='Target Shapes',
        type=TargetShapes,
        description='Target Shapes for this ARKit shape. Multiple target shapes possible',
        options=set(),
    )
    draw_alert: BoolProperty(default=False)

    warnings: StringProperty(
        name='Warnigns',
        default=''
    )
    amplify: FloatProperty(
        name='Amplify Value',
        default=1.0,
        description='Use the Amplify Value to increasing or decreasing the motion of this expression.',
        soft_min=0.0,
        soft_max=10.0,
    )


# --------------- FUNCTIONS --------------------
# | - Update/Getter/Setter
# ----------------------------------------------


def update_retargeting_scheme(self, context):
    if context is None:
        return
    if self.faceit_retarget_shapes:
        bpy.ops.faceit.change_retargeting_name_scheme()


def update_retarget_index(self, context):
    if context is None:
        return
    if self.faceit_retarget_shapes:
        if self.faceit_sync_shapes_index:
            active_shape_item = self.faceit_retarget_shapes[self.faceit_retarget_shapes_index]
            if active_shape_item:
                shape_name = active_shape_item.name
                bpy.ops.faceit.set_active_shape_key_index(
                    'EXEC_DEFAULT', shape_name=shape_name, get_arkit_target_shapes=True)


def update_shape_sync(self, context):
    if context is None:
        return
    if self.faceit_sync_shapes_index:
        active_shape_item = self.faceit_retarget_shapes[self.faceit_retarget_shapes_index]
        if active_shape_item:
            bpy.ops.faceit.set_active_shape_key_index(
                'EXEC_DEFAULT', shape_name=active_shape_item.name, get_arkit_target_shapes=True)

# --------------- REGISTER/UNREGISTER --------------------


def register():
    ############## Retargeting Shapes ##################

    Scene.faceit_retarget_shapes = CollectionProperty(
        name='ARKIT Target Expressions',
        type=Retarget_Shapes,
    )

    Scene.faceit_retarget_shapes_index = IntProperty(
        name='Expression Index',
        default=0,
        update=update_retarget_index,
        options=set(),
    )

    Scene.faceit_sync_shapes_index = BoolProperty(
        name='Sync Selection',
        default=False,
        update=update_shape_sync,
        description='Synchronize the index in the active faceit shape and the active shape key on all registered objects'
    )
    Scene.faceit_shape_key_lock = BoolProperty(
        name='Show Only Active',
        default=False,
        update=update_shape_sync,
        description='Show only the active shape key on all registered objects'
    )

    Scene.faceit_retargeting_naming_scheme = EnumProperty(
        items=(
            ('ARKIT', 'ARKit Native', 'ARKit Native'),
            ('FACECAP', 'FaceCap', 'bannaflak FaceCap'),
            # ('RETARGET', 'Retarget List', 'Based on Retargeting List'),
        ),
        default='ARKIT',
        update=update_retargeting_scheme,
    )


def unregister():
    del Scene.faceit_retarget_shapes
    del Scene.faceit_retarget_shapes_index
    del Scene.faceit_sync_shapes_index
    del Scene.faceit_shape_key_lock
    del Scene.faceit_retargeting_naming_scheme
