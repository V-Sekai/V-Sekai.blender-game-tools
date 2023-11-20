import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       IntProperty, PointerProperty, StringProperty, FloatProperty)
from bpy.types import Object, PropertyGroup, Scene, Armature, Modifier, FCurve, ID


from ..core import faceit_utils as futils

# --------------- CLASSES --------------------
# | - Property Groups (Collection-/PointerProperty)
# ----------------------------------------------


# class FaceitDriverTargets(PropertyGroup):
#     id_type: EnumProperty(
#         items=[
#             ('ACTION', 'Action', 'Action'),
#             ('ARMATURE', 'Armature', 'Armature'),
#             ('BRUSH', 'Brush', 'Brush'),
#             ('CACHEFILE', 'Cache File', 'Cache File'),
#             ('CAMERA', 'Camera', 'Camera'),
#             ('COLLECTION', 'Collection', 'Collection'),
#             ('CURVE', 'Curve', 'Curve'),
#             ('CURVES', 'Curves', 'Curves'),
#             ('FONT', 'Font', 'Font'),
#             ('GREASEPENCIL', 'Grease Pencil', 'Pencil'),
#             ('IMAGE', 'Image', 'Image'),
#             ('KEY', 'Key', 'Key'),
#             ('LATTICE', 'Lattice', 'Lattice'),
#             ('LIBRARY', 'Library', 'Library'),
#             ('LIGHT', 'Light', 'Light'),
#             ('LIGHT_PROBE', 'Light Probe', 'Probe'),
#             ('LINESTYLE', 'Line Style', 'Style'),
#             ('MASK', 'Mask', 'Mask'),
#             ('MATERIAL', 'Material', 'Material'),
#             ('MESH', 'Mesh', 'Mesh'),
#             ('META', 'Metaball', 'Metaball'),
#             ('MOVIECLIP', 'Movie Clip', 'Clip'),
#             ('NODETREE', 'Node Tree', 'Tree'),
#             ('OBJECT', 'Object', 'Object'),
#             ('PAINTCURVE', 'Paint Curve', 'Curve'),
#             ('PALETTE', 'Palette', 'Palette'),
#             ('PARTICLE', 'Particle', 'Particle'),
#             ('POINTCLOUD', 'Point Cloud', 'Cloud'),
#             ('SCENE', 'Scene', 'Scene'),
#             ('SIMULATION', 'Simulation', 'Simulation'),
#             ('SOUND', 'Sound', 'Sound'),
#             ('SPEAKER', 'Speaker', 'Speaker'),
#             ('TEXT', 'Text', 'Text'),
#             ('TEXTURE', 'Texture', 'Texture'),
#             ('VOLUME', 'Volume', 'Volume'),
#             ('WINDOWMANAGER', 'Window Manager', 'Window Manager'),
#             ('WORKSPACE', 'Workspace', 'Workspace'),
#             ('WORLD', 'World', 'World'),
#         ]
#     )
#     id: PointerProperty(
#         type=ID,
#     )
#     id_is_self: BoolProperty()
#     bone_target: StringProperty()
#     transform_type: EnumProperty(
#         items=[
#             ('LOC_X', 'Location X', 'Location X'),
#             ('LOC_Y', 'Location Y', 'Location Y'),
#             ('LOC_Z', 'Location Z', 'Location Z'),
#             ('ROT_X', 'Rotation X', 'Rotation X'),
#             ('ROT_Y', 'Rotation Y', 'Rotation Y'),
#             ('ROT_Z', 'Rotation Z', 'Rotation Z'),
#             ('ROT_W', 'Rotation W', 'Rotation W'),
#             ('SCALE_X', 'Scale X', 'Scale X'),
#             ('SCALE_Y', 'Scale Y', 'Scale Y'),
#             ('SCALE_Z', 'Scale Z', 'Scale Z'),
#             ('SCALE_AVG', 'Scale Average', 'Scale Average'),
#         ]
#     )
#     transform_space: EnumProperty(
#         items=[
#             ('WORLD_SPACE', 'World Space', 'World Space'),
#             ('TRANSFORM_SPACE', 'Transform Space', 'Transform Space'),
#             ('LOCAL_SPACE', 'Local', 'Local'),
#         ]
#     )
#     rotation_mode: EnumProperty(
#         items=[
#             ('AUTO', 'Auto Euler', 'Euler using the rotation order of the target.'),
#             ('XYZ', 'XYZ Euler', 'XYZ Euler rotation order.'),
#             ('XZY', 'XZY Euler', 'XZY Euler rotation order.'),
#             ('YXZ', 'YXZ Euler', 'YXZ Euler rotation order.'),
#             ('YZX', 'YZX Euler', 'YZX Euler rotation order.'),
#             ('ZXY', 'ZXY Euler', 'ZXY Euler rotation order.'),
#             ('ZYX', 'ZYX Euler', 'ZYX Euler rotation order.'),
#             ('QUATERNION', 'Quaternion', 'Quaternion rotation order.'),
#             ('SWING_TWIST_X', 'Swing Twist X', 'Swing Twist X rotation order.'),
#             ('SWING_TWIST_Y', 'Swing Twist Y', 'Swing Twist Y rotation order.'),
#             ('SWING_TWIST_Z', 'Swing Twist Z', 'Swing Twist Z rotation order.'),
#         ]
#     )
#     data_path: StringProperty()


# class FaceitDriverVariables(PropertyGroup):
#     '''Collection of driver variables'''
#     # is_name_valid (readonly)
#     name: StringProperty(name='Name', default='')
#     targets: CollectionProperty(type=FaceitDriverTargets)
#     type: EnumProperty(
#         items=[
#             ('SINGLE_PROP', 'Single Property', 'Single Property'),
#             ('TRANSFORMS', 'Transforms', 'Transforms'),
#             ('ROTATION_DIFF', 'Rotation Difference', 'Rotation Difference'),
#             ('LOC_DIFF', 'Location Difference', 'Location Difference'),
#         ]
#     )


# class FaceitDrivers(PropertyGroup):
#     '''Collection of drivers'''
#     expression: StringProperty(name='Expression', default='')
#     # is_simple_expression(readonly)
#     # is_valid(readonly)
#     type: EnumProperty(
#         items=[
#             ('AVERAGE', 'Average', 'Average'),
#             ('SUM', 'Sum', 'Sum'),
#             ('SCRIPTED', 'Scripted', 'Scripted'),
#             ('MIN', 'Minimum', 'Minimum'),
#             ('MAX', 'Maximum', 'Maximum'),
#         ]
#     )
#     use_self: BoolProperty(name='Use Self', default=False)
#     variables: CollectionProperty(type=FaceitDriverVariables)


# class FaceitDriverFcurves(PropertyGroup):
#     '''Collection of (driver) fcurves'''
#     data_path: StringProperty(name='Data Path', default='')
#     array_index: IntProperty(name='Array Index', default=0)
#     auto_smoothing: EnumProperty(
#         items=[
#             ('NONE', 'None', 'None'),
#             ('CONT_ACCEL', 'Continuous Acceleration', 'Continuous Acceleration'),
#         ]
#     )
#     color_mode: EnumProperty(
#         items=[
#             ('AUTO_RAINBOW', 'Auto Rainbow', 'Auto Rainbow'),
#             ('AUTO_RGB', 'Auto RGB', 'Auto RGB'),
#             ('AUTO_YRGB', 'Auto YRGB', 'Auto YRGB'),
#             ('CUSTOM', 'Custom', 'Custom'),
#         ]
#     )
#     extrapolation: EnumProperty(
#         items=[
#             ('CONSTANT', 'Constant', 'Constant'),
#             ('LINEAR', 'Linear', 'Linear'),
#         ]
#     )
#     group: StringProperty(name='Group', default='')

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


def update_masked(self, context):
    # Start the operator, closes automatically when the property is changed
    bpy.ops.faceit.mask_group(
        'INVOKE_DEFAULT',
        vgroup_name=self.name,
        operation='ADD' if self.is_masked else 'REMOVE',
        # prop=self.name
    )


class AssignedObjects(PropertyGroup):
    name: StringProperty(
        name='Object Name'
    )


class FaceitVertexGroups(PropertyGroup):
    name: StringProperty(
        name='Vertex Group Name',
        description='Vertex group name'
    )
    is_drawn: BoolProperty(
        name='Draw Assigned',
        default=False
    )
    is_assigned: BoolProperty(
        name='Is Assigned',
    )
    is_masked: BoolProperty(
        name='Is Masked',
        default=False,
        description='Is this vertex group a mask?',
    )
    mask_inverted: BoolProperty(
        name='Invert Mask',
        default=True,
        description='Invert the mask',
    )
    assigned_to_objects: CollectionProperty(
        name='Assigned To Objects',
        type=AssignedObjects
    )

    def assign_object(self, obj_name):
        if obj_name in self.assigned_to_objects:
            return
        item = self.assigned_to_objects.add()
        item.name = obj_name
        self.is_assigned = True

    def remove_object(self, obj_name):
        idx = self.assigned_to_objects.find(obj_name)
        if idx != -1:
            self.assigned_to_objects.remove(idx)
            if not self.assigned_to_objects:
                self.is_assigned = False

    # assigned_to_objects: StringProperty(
    #     name='Assigned To Objects',
    #     default=''
    # )
    # def assign_object(self, object_name):
    #     assigned_to = self.assigned_to_objects.split(';;')
    #     if object_name not in assigned_to:
    #         self.assigned_to_objects += object_name + ';;'
    #     print(self.assigned_to_objects.split(';;'))

    # def get_assigned_object_names(self):
    #     ''''''
    #     assigned_to = self.assigned_to_objects.split(';;')
    #     return [x for x in assigned_to if x != '']
    #     # return self.assigned_to_objects.split(';;')

    # def remove_object(self, object_name):
    #     '''Remove an object'''
    #     assigned_to = self.assigned_to_objects.split(';;')
    #     if object_name in assigned_to:
    #         assigned_to.remove(object_name)
    #     self.assigned_to_objects = ''
    #     for x in assigned_to:
    #         self.assigned_to_objects += x + ';;'

    # --------------- FUNCTIONS --------------------
    # | - Update/Getter/Setter
    # ----------------------------------------------


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
    Scene.faceit_vertex_groups = CollectionProperty(
        type=FaceitVertexGroups
    )


def unregister():
    del Scene.faceit_face_objects
    del Scene.faceit_subscribed
    del Scene.faceit_face_index
    del Scene.faceit_show_warnings
