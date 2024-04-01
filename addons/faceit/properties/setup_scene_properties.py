import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       IntProperty, PointerProperty, StringProperty, FloatProperty)
from bpy.types import Object, PropertyGroup, Scene, Armature, Modifier, FCurve, ID


from ..core import faceit_utils as futils


class FaceitBakeModDrivers(PropertyGroup):
    data_path: StringProperty(name='Data Path', default='')
    is_muted: BoolProperty(name='Mute', default=False)


class FaceitBakeModifiers(PropertyGroup):
    '''
    Collection of modifiers on faceit objects that can be baked to shape keys.
    Bakeable modifiers are:
    - ARMATURE
    - SURFACE_DEFORM
    - SHRINKWRAP
    '''
    name: StringProperty(
        name="Modifier Name",
    )
    type: StringProperty(
        name="Modifier Type",
    )
    is_faceit_modifier: BoolProperty()
    # obj_item: PointerProperty(
    #     name="Faceit Object",
    #     type=FaceitObjects,
    # )
    can_bake: BoolProperty(
        name="Can Bake",
        default=False,
        description="Whether this modifier can be baked to shape keys",
    )
    bake: BoolProperty(
        name='Bake',
        default=False,
        description='Bake this modifier to shape keys.'
    )
    recreate: BoolProperty(
        name='Restore',
        description='Restore this modifier if it can\'t be found',
        default=False,
    )
    mod_icon: StringProperty(
        name="Modifier Icon",
        default='MODIFIER',
    )
    index: IntProperty()
    # Modifier properties
    show_viewport: BoolProperty(
        name="Show"
    )
    show_render: BoolProperty(
        name="Show"
    )
    show_in_editmode: BoolProperty(
        name="Show"
    )
    show_on_cage: BoolProperty(
        name="Show"
    )
    show_expanded: BoolProperty(
        name="Show"
    )
    show_in_editmode: BoolProperty(
        name="Show"
    )
    show_in_editmode: BoolProperty(
        name="Show"
    )
    drivers: CollectionProperty(
        name="Drivers",
        type=FaceitBakeModDrivers
    )
    # is_active
    # use_apply_on_spline
    # is_override_data
    # SURFACE_DEFORM
    is_bound: BoolProperty()
    falloff: FloatProperty()
    invert_vertex_group: BoolProperty()
    strength: FloatProperty()
    target: PointerProperty(type=Object)
    use_sparse_bind: BoolProperty()
    vertex_group: StringProperty()
    # SHRINKWRAP
    auxilliary_target: PointerProperty(type=Object)
    cull_face: EnumProperty(
        items=(
            ('OFF', 'Off', 'Off'),
            ('FRONT', 'Front', 'Front'),
            ('BACK', 'Back', 'Back'),
        )
    )
    offset: FloatProperty()
    project_limit: FloatProperty()
    subsurf_levels: IntProperty()
    use_invert_cull: BoolProperty()
    use_negative_direction: BoolProperty()
    use_positive_direction: BoolProperty()
    use_project_x: BoolProperty()
    use_project_y: BoolProperty()
    use_project_z: BoolProperty()
    wrap_method: EnumProperty(
        items=(
            ('NEAREST_SURFACEPOINT', 'Nearest Surfacepoint', 'Nearest Surfacepoint'),
            ('PROJECT', 'Project', 'Project'),
            ('NEAREST_VERTEX', 'Nearest Vertex', 'Nearest Vertex'),
            ('TARGET_PROJECT', 'Target Project', 'Target Project'),
        )
    )
    wrap_mode: EnumProperty(
        items=(
            ('ON_SURFACE', 'On Surface', 'On Surface'),
            ('INSIDE', 'Inside', 'Inside'),
            ('OUTSIDE', 'Outside', 'Outside'),
            ('OUTSIDE_SURFACE', 'Outside Surface', 'Outside Surface'),
            ('ABOVE_SURFACE', 'Above Surface', 'Above Surface'),
        )
    )
    # ARMATURE
    object: PointerProperty(type=Object)
    use_bone_envelopes: BoolProperty()
    use_deform_preserve_volume: BoolProperty()
    use_multi_modifier: BoolProperty()
    use_vertex_groups: BoolProperty()
    # CORRECTIVE SMOOTH
    factor: FloatProperty()
    is_bind: BoolProperty()
    iterations: IntProperty()
    smooth_type: EnumProperty(
        items=(
            ('ORCO', 'Original Coordinates', 'Original Coordinates'),
            ('BIND', 'Bind Coordinates', 'Bind Coordinates'),
        )
    )
    scale: FloatProperty()
    smooth_type: EnumProperty(
        items=(
            ('SIMPLE', 'Simple', 'Simple'),
            ('LENGTH_WEIGHTED', 'Length Weight', 'Length Weight'),
        )
    )
    use_only_smooth: BoolProperty()
    use_pin_boundary: BoolProperty()
    # LATTICE
    # object
    # strength
    # SMOOTH
    # factor
    # iterations
    use_x: BoolProperty()
    use_y: BoolProperty()
    use_z: BoolProperty()
    # LAPLACIANSMOOTH
    # iterations
    lambda_border: FloatProperty()
    lambda_factor: FloatProperty()
    use_normalized: BoolProperty()
    use_volume_preserve: BoolProperty()
    # use_x
    # use_y
    # use_z
    # MESH_DEFORM
    precision: IntProperty()
    use_dynamic_bind: BoolProperty()
    # object
    # is_bound


def update_mod_index(self, context):
    '''Set the active modifier when the faceit_modifiers list index changes.'''
    face_item = self
    bpy.context.scene.faceit_face_index = bpy.context.scene.faceit_face_objects.find(face_item.name)
    obj = futils.get_object(face_item.name)
    if obj:
        mod = obj.modifiers[face_item.active_mod_index]
        if mod:
            obj.modifiers.active = mod
            # mod.show_expanded = True


class FaceitObjects(PropertyGroup):
    name: StringProperty(
        name='Object Name',
        description='object name'
    )
    # Problem with object ids, they have to be deleted globally,
    # otherwise they will never be none. Even if deleted from scene..
    obj_pointer: PointerProperty(
        name='Object',
        type=Object
    )
    part: StringProperty(
        name='Facial Part',
        description='The facial part that this object represents'
    )
    warnings: StringProperty(
        name='Warnigns',
        default=''
    )
    modifiers: CollectionProperty(
        name='Faceit Modifiers',
        type=FaceitBakeModifiers,
    )
    active_mod_index: IntProperty(
        name="Active Modifier Index",
        default=0,
        update=update_mod_index
    )

    def get_object(self):
        return futils.get_object(self.name)


class PickerOptions(PropertyGroup):
    hide_assigned: BoolProperty(
        name='Hide Assigned',
        default=True,
        description='Hide all vertices that are already assigned to a Faceit Vertex Group.'
    )
    pick_geometry: EnumProperty(
        name='Pick Geometry',
        items=(
            ('SURFACE', 'Surface', 'Assign based on connected vertices (Surfaces/Islands)'),
            ('OBJECT', 'Object', 'Assign the vertex group to the entire object'),
        ),
        default='SURFACE',
    )
    picking_group: StringProperty(
        name='Picking Group',
        description='The vertex group that is currently being picked',
        default='',
    )


def update_object_index(self, context):
    '''Set the active object when the faceit_objects list index changes.'''
    scene = self
    faceit_objects = scene.faceit_face_objects
    index = scene.faceit_face_index
    item = faceit_objects[index]
    object_name = item.name
    if context.active_object:
        if object_name != context.active_object.name or context.selected_objects != [context.active_object]:
            if context.active_object.hide_viewport is False:
                bpy.ops.object.mode_set(mode='OBJECT')
        else:
            return
    if futils.get_object(object_name):
        bpy.ops.faceit.select_facial_part('INVOKE_DEFAULT', object_name=object_name)
    else:
        scene.faceit_face_objects.remove(index)


def register():

    Scene.faceit_face_objects = CollectionProperty(
        type=FaceitObjects
    )
    Scene.faceit_subscribed = BoolProperty(
        name="Subscribed",
        default=False,
        description="Whether the msgbus is subscribed to the active object"
    )
    Scene.faceit_face_index = IntProperty(
        default=0,
        update=update_object_index
    )

    Scene.faceit_show_warnings = BoolProperty(
        name='Show Warnings',
        default=False,
    )
    Scene.faceit_picker_options = PointerProperty(
        name='Picker Options',
        type=PickerOptions
    )


def unregister():
    del Scene.faceit_face_objects
    del Scene.faceit_subscribed
    del Scene.faceit_face_index
    del Scene.faceit_show_warnings
    del Scene.faceit_picker_options
