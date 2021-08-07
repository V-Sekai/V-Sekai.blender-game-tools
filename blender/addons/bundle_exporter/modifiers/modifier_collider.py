import bpy
import math
import imp
import mathutils

from . import modifier
from ..settings import engines, ue4_collider_prefixes

# https://blenderartists.org/t/generate-bounding-boxes-for-selected-objects/559218


def create_box_collider(obj, engine):
    new_obj = None
    bpy.context.view_layer.objects.active = obj
    if bpy.context.object.mode == 'OBJECT':
        scale = obj.scale

        minx = obj.bound_box[0][0] * scale.x
        maxx = obj.bound_box[4][0] * scale.x
        miny = obj.bound_box[0][1] * scale.y
        maxy = obj.bound_box[2][1] * scale.y
        minz = obj.bound_box[0][2] * scale.z
        maxz = obj.bound_box[1][2] * scale.z
        dx = maxx - minx
        dy = maxy - miny
        dz = maxz - minz

        loc = mathutils.Vector(((minx + 0.5 * dx), (miny + 0.5 * dy), (minz + 0.5 * dz)))
        loc.rotate(obj.rotation_euler)
        loc = loc + obj.location

        bpy.ops.mesh.primitive_cube_add(location=loc, rotation=obj.rotation_euler)
        new_obj = bpy.context.object

        new_obj.name = 'UBX_' + obj.name
        new_obj.dimensions = mathutils.Vector((dx, dy, dz))

        new_obj.users_collection[0].objects.unlink(new_obj)
        obj.users_collection[0].objects.link(new_obj)
    elif bpy.context.object.mode == 'EDIT':
        orig_objects = bpy.context.selected_objects[:]
        bpy.ops.mesh.duplicate(mode=1)
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        dup = next(x for x in bpy.context.selected_objects if x not in orig_objects)
        new_obj = create_box_collider(dup, engine)
        bpy.ops.object.select_all(action='DESELECT')
        dup.select_set(True)
        bpy.ops.object.delete()
        obj.select_set(True)

    return new_obj


class BGE_mod_collider(modifier.BGE_mod_default):
    label = "Export Colliders"
    id = 'collider'
    url = "http://renderhjs.net/fbxbundle/#modifier_collider"
    type = 'GENERAL'
    icon = 'CUBE'
    priority = 999  # just after rename
    tooltip = 'Setups collision meshes properly. It also has options to automatically create them'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    ratio: bpy.props.FloatProperty(
        default=0.35,
        min=0.01,
        max=1,
        description="Ratio of triangle count to orginal mesh",
        subtype='FACTOR'
    )

    angle: bpy.props.FloatProperty(
        default=40,
        min=5,
        max=55,
        description="Reduction angle in degrees",
        subtype='FACTOR'
    )

    show_extras: bpy.props.BoolProperty(
        default=True
    )

    engine: bpy.props.EnumProperty(
        name="Engine",
        items=engines,
    )

    collider_creation: bpy.props.BoolProperty(
        default=False
    )

    generate_process: bpy.props.EnumProperty(
        name='Generate With',
        items=[
            ('BOX', 'Box', 'By Bounds'),
            ('DECIMATION', 'Decimation', 'By reducing poligon count of the other meshes')
        ]
    )

    def _draw_info(self, layout):
        layout.prop(self, "engine")

        layout.prop(self, "collider_creation")

        if self.collider_creation:
            layout.prop(self, "generate_process")
            if self.generate_process == 'DECIMATION':
                row = layout.row(align=True)
                row.prop(self, "ratio", text="Ratio", icon='AUTOMERGE_ON')
                row.prop(self, "angle", text="Angle", icon='AUTOMERGE_ON')

        box = layout.box()
        row = box.row(align=True)
        row.prop(
            self,
            'show_extras',
            icon="TRIA_DOWN" if self.show_extras else "TRIA_RIGHT",
            icon_only=True,
            text='Operators',
            emboss=False
        )
        if self.show_extras:
            box.operator('bge.create_box_collider').engine = self.engine

    def _get_ue_collider_prefix(self, name):
        for prefix in ue4_collider_prefixes:
            if name.startswith(prefix):
                return prefix

        assert False

    def _get_colliders(self, objects, pop=True):
        colliders = []
        for i in reversed(range(0, len(objects))):
            if self.engine == 'UNREAL':
                for prefix in ue4_collider_prefixes:
                    if objects[i].name.startswith(prefix):
                        colliders.append(objects[i])
                        if pop:
                            objects.pop(i)
                        break
        return colliders

    # TODO: do the same with lods
    def pre_process(self, bundle_info):
        # remove possible colliders from being treated as a mesh
        bundle_info['extras'] = self._get_colliders(bundle_info['meshes'], pop=True)

    def process(self, bundle_info):
        # UNITY 	https://docs.unity3d.com/Manual/LevelOfDetail.html
        # UNREAL 	https://docs.unrealengine.com/en-us/Engine/Content/Types/StaticMeshes/HowTo/LODs
        # 			https://answers.unrealengine.com/questions/416995/how-to-import-lods-as-one-fbx-blender.html
        objects = bundle_info['meshes']
        if not objects:
            return

        if self.collider_creation:
            if self.generate_process == 'BOX':
                for obj in objects:
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
                    col = create_box_collider(obj, self.engine)
                    col['__IS_COPY__'] = True  # to automatically delete them after export
                    bundle_info['extras'].append(col)
            if self.generate_process == 'DECIMATION':
                for obj in objects:
                    # Select
                    bpy.ops.object.select_all(action="DESELECT")
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj

                    # Copy & Decimate modifier
                    bpy.ops.object.duplicate()
                    bpy.context.object.name = "{}_COLLIDER".format(obj.name)
                    copy = bpy.context.object

                    # Display as wire
                    # copy.draw_type = 'WIRE'
                    # copy.show_all_edges = True
                    # Decimate A
                    mod = copy.modifiers.new("RATIO", type='DECIMATE')
                    mod.ratio = self.ratio

                    # Displace
                    mod = copy.modifiers.new("__displace", type='DISPLACE')
                    mod.mid_level = 0.85
                    mod.show_expanded = False

                    # Decimate B
                    mod = copy.modifiers.new("ANGLE", type='DECIMATE')
                    mod.decimate_type = 'DISSOLVE'
                    mod.angle_limit = self.angle * math.pi / 180

                    # Triangulate
                    mod = copy.modifiers.new("__triangulate", type='TRIANGULATE')
                    mod.show_expanded = False

                    # Triangulate
                    mod = copy.modifiers.new("__shrinkwrap", type='SHRINKWRAP')
                    mod.target = obj
                    mod.show_expanded = False

                    # bpy.ops.object.modifier_add(type='DECIMATE')
                    # bpy.context.object.modifiers["Decimate"].ratio = get_quality(i, self.levels, self.quality)
                    copy['__IS_COPY__'] = True  # to automatically delete them after export

                    # add them to "extras" so other modifiers won't process them
                    bundle_info['extras'].append(copy)

        # rename and parent (required for unreal engine)
        parent_object = bundle_info['meshes'][0]
        if parent_object:
            colliders = self._get_colliders(bundle_info['extras'], pop=False)
            for index, x in enumerate(colliders):
                if x.parent and x.parent in bundle_info['meshes']:
                    parent_object = x.parent
                prefix = self._get_ue_collider_prefix(x.name)
                x.name = '{}_{}_{}'.format(prefix, parent_object.name, index)
                x.parent = parent_object
                x.matrix_parent_inverse = parent_object.matrix_world.inverted()
