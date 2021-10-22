import bpy
import imp
import string
import random
from mathutils import Vector

from . import modifier
from ..settings import ue4_collider_prefixes


class BGE_mod_merge_meshes(modifier.BGE_mod_default):
    label = "Merge Meshes"
    id = 'merge'
    url = "http://renderhjs.net/fbxbundle/#modifier_merge"
    type = 'MESH'
    icon = 'SELECT_EXTEND'
    priority = 0
    tooltip = 'Merges meshes when exporting'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    merge_verts: bpy.props.BoolProperty(
        name="Merge",
        description="Merges vertices by distance (Remove Doubles)",
        default=False
    )

    merge_by_material: bpy.props.BoolProperty(
        name="By Material",
        description="Split meshes by material after merging.",
        default=False
    )

    merge_distance: bpy.props.FloatProperty(
        name="Dist.",
        default=0,
        min=0,
        description="Minimum distance of verts to merge. Set to 0 to disable.",
        subtype='DISTANCE'
    )

    merge_type: bpy.props.EnumProperty(
        name='Merge Type',
        items=[
            ('ALL', 'All', 'Merge all meshes into one mesh'),
            ('COLLECTION', 'By Collection', 'Groups objects by their corresponding collections and merges them'),
            ('PARENT', 'By Parent', 'Merges all meshes with their children')
        ]
    )

    keep_armature_modifier: bpy.props.BoolProperty(
        default=True
    )

    merge_uvs_by_index: bpy.props.BoolProperty(
        name="Merge UVs by index",
        description="Merges UVs by index instead of by name",
        default=True
    )
    # consistent_normals = bpy.props.BoolProperty (
    # 	name="Make consistent Normals",
    # 	default=True
    # )

    def _draw_info(self, layout):
        row = layout.row()

        col = row.column(align=False)

        col.prop(self, 'merge_type')

        col = col.column(align=True)

        row = col.row(align=True)
        row.prop(self, "merge_verts", text="Merge Verts")
        row_freeze = row.row()
        row_freeze.enabled = self.merge_verts
        row_freeze.prop(self, "merge_distance")

        row = col.row(align=True)
        row.prop(self, "merge_by_material", text="Split by Material")

        row = col.row(align=True)
        row.prop(self, 'keep_armature_modifier', text="Try to keep armature")

        row = col.row(align=True)
        row.prop(self, 'merge_uvs_by_index', text="Merge UVs by index")

    def process(self, bundle_info):
        name = bundle_info['name']
        objects = bundle_info['meshes']
        armatures = bundle_info['armatures']
        pivot = bundle_info['pivot']
        if len(objects) < 2:
            return

        if self.merge_type == 'ALL':
            objects = self.merge_meshes(objects, armatures, name, pivot)

        elif self.merge_type == 'COLLECTION':
            # gather all collections
            collections_dict = {}
            for x in objects:
                obj_collection = x['__orig_collection__']
                if obj_collection not in collections_dict:
                    collections_dict[obj_collection] = []
                collections_dict[obj_collection].append(x)
            # empty the result list
            objects = []
            # merge by gathered objects
            for collection_name, objs in collections_dict.items():
                merged = self.merge_meshes(objs, armatures, collection_name, pivot)
                # rename all merged objects to the name of the collection
                for obj in merged:
                    obj.name = collection_name
                # repopulate export list
                objects.extend(merged)

        elif self.merge_type == 'PARENT':
            parents = {}
            for obj in reversed(objects):
                parent = obj.parent
                if parent and parent in objects:
                    while parent and parent.parent and parent.parent in objects:
                        parent = parent.parent
                    if parent not in parents:
                        parents[parent] = []

                    parents[parent].append(obj)
                elif obj not in parents:
                    parents[obj] = []

            objects = []

            for parent, children in parents.items():
                merged = self.merge_meshes([parent] + children, armatures, parent.name, pivot)
                objects.extend(merged)

        bundle_info['meshes'] = objects

    def merge_meshes(self, objects, armatures, name, pivot):

        if len(objects) < 2:
            return objects

        bpy.ops.object.select_all(action='DESELECT')

        armature_dict = {}
        if self.keep_armature_modifier:
            for x in objects:
                for mod in x.modifiers:
                    if mod.type == 'ARMATURE':
                        armature_dict = {y.identifier: getattr(mod, y.identifier) for y in mod.bl_rna.properties if not y.is_readonly}
                        break

                x.select_set(True)
        else:
            for x in objects:
                x.select_set(True)

        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # Convert to mesh
        bpy.ops.object.convert(target='MESH')

        if self.merge_uvs_by_index:
            uv_names = []
            for x in objects:
                for index, uv in enumerate(x.data.uv_layers):
                    if len(uv_names) < index:
                        uv_names.append(uv.name)
                    uv.name = '__{}__'.format(index)
            # for x in objects:
            #    for index, uv in enumerate(x.data.uv_layers):
            #        uv.name = uv_names[index]

        # Merge objects into single item
        bpy.ops.object.join()
        new_objects = [bpy.context.object]
        bpy.context.object.name = name  # assign bundle name
        bpy.context.scene.cursor.location = pivot
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

        # Apply rotation
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

        # Merge Vertices?
        if self.merge_verts and self.merge_distance > 0:

            bpy.ops.object.mode_set(mode='EDIT', toggle=False)
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
            bpy.ops.mesh.select_all(action='SELECT')

            bpy.ops.mesh.remove_doubles(threshold=self.merge_distance)

            bpy.ops.mesh.quads_convert_to_tris()

            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        # if self.consistent_normals :
        # 	bpy.ops.object.mode_set(mode='EDIT')
        # 	bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
        # 	bpy.ops.mesh.select_all(action='SELECT')

        # 	bpy.ops.mesh.normals_make_consistent(inside=False)

        # 	bpy.ops.mesh.select_all(action='DESELECT')
        # 	bpy.ops.object.mode_set(mode='OBJECT')

        if self.merge_by_material:
            # TODO: Split faces by materials

            bpy.ops.object.mode_set(mode='EDIT', toggle=False)
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')

            # Rename with unique ID
            prefix = "{}_{}".format(name, id_generator())

            mats = {}
            for i in range(0, len(bpy.context.object.material_slots)):

                slot = bpy.context.object.material_slots[i]
                if slot.material and slot.material not in mats:
                    # Store prefx by material
                    prefix_mat = "{}_{}".format(prefix, slot.material.name)

                    bpy.context.object.name = prefix_mat

                    mat = slot.material
                    mats[mat] = prefix_mat

                    if len(bpy.context.object.data.vertices) > 0:
                        bpy.ops.mesh.select_all(action='DESELECT')
                        bpy.context.object.active_material_index = i
                        bpy.ops.object.material_slot_select()
                        if len([v for v in bpy.context.active_object.data.vertices if v.select]) > 0:
                            bpy.ops.mesh.separate(type='SELECTED')

            bpy.ops.object.mode_set(mode='OBJECT')

            mat_objs = []
            for obj in bpy.context.scene.objects:
                if prefix in obj.name:
                    if len(obj.data.vertices) == 0:
                        bpy.ops.object.select_all(action='DESELECT')
                        obj.select_set(True)
                        bpy.ops.object.delete()
                    else:
                        mat_objs.append(obj)

            # Combine & Rename by materials
            for mat in mats:
                prefix_mat = mats[mat]
                for obj in mat_objs:

                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)

                    if prefix_mat in obj.name:

                        for i in range(len(obj.material_slots) - 1):
                            bpy.ops.object.material_slot_remove()
                        obj.material_slots[0].material = mat

                        obj.name = "{}_{}".format(name, mat.name)

            # return material objects
            new_objects = mat_objs

        objects = new_objects

        if armature_dict:
            for x in objects:
                mod = x.modifiers.new('MergeArmature', 'ARMATURE')
                for prop, value in armature_dict.items():
                    setattr(mod, prop, value)
                if armatures and mod.object not in armatures:
                    mod.object = armatures[0]

        return objects


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))
