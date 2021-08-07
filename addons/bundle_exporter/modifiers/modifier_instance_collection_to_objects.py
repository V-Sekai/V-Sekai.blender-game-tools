import bpy
import bmesh
import mathutils
import imp

from . import modifier
from .. import settings
from ..utilities import traverse_tree


class BGE_mod_instance_collection_to_objects(modifier.BGE_mod_default):
    label = "Group Intstances to Objects"
    id = 'instance_collection_to_objects'
    url = "http://renderhjs.net/fbxbundle/"
    type = 'GENERAL'
    icon = 'OUTLINER_OB_GROUP_INSTANCE'
    priority = -999
    tooltip = 'Instance collections will be converted to objects when exporting'

    active: bpy.props.BoolProperty(
        name="Active",
        default=False
    )

    show_info: bpy.props.BoolProperty(
        name="Show Info",
        default=True
    )

    export_hidden: bpy.props.BoolProperty(
        name="Export Hidden",
        default=False
    )

    def _draw_info(self, layout):
        layout.prop(self, 'export_hidden')

    def pre_process(self, bundle_info):
        helpers = bundle_info['empties']
        if not helpers:
            return
        for i in reversed(range(0, len(helpers))):
            x = helpers[i]
            if x.instance_type == 'COLLECTION' and x.instance_collection:

                orig_collection = x.instance_collection
                orig_objects = [x for x in bpy.data.objects]

                if not self.export_hidden:
                    for collection in traverse_tree(x.instance_collection):
                        for obj in collection.objects:
                            obj['__do_export__'] = not (collection['__orig_hide__'] or ('__orig_hide_lc__' in collection and collection['__orig_hide_lc__']) or ('__orig_hide__' in obj and obj['__orig_hide__']))

                bpy.ops.object.select_all(action='DESELECT')
                x.select_set(True)
                bpy.ops.object.duplicates_make_real(use_base_parent=False, use_hierarchy=True)
                new_nodes = [obj for obj in bpy.context.scene.objects if obj.select_get() and obj != x]
                bpy.ops.object.make_local(type='SELECT_OBDATA')
                bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True, material=False, animation=False)

                # search custom attribs on empty and apply them to the objects
                coll_dict = {key: x[key] for key in x.keys() if not key.startswith('_')}
                for new_node in new_nodes:
                    for key in coll_dict:
                        new_node[key] = coll_dict[key]
                    new_node['__IS_COPY__'] = True  # to automatically delete them after export

                    #  time to copy drivers, they are lost when making collections real (https://developer.blender.org/T70551)
                    try:
                        orig_node = next(obj for obj in orig_objects if obj['__orig_name__'] == new_node['__orig_name__'])
                    except StopIteration:
                        print('COULD NOT COPY DRIVERS FOR {}'.format(new_node['__orig_name__']))
                        continue
                    if orig_node.animation_data:
                        if not new_node.animation_data:
                            new_node.animation_data_create()
                        for orig_driver in orig_node.animation_data.drivers:
                            # copying this driver makes blender crash when using merge armatures modifier, it does not change the export result so lets just ignore it
                            if 'hide_viewport' in orig_driver.data_path:
                                continue
                            try:
                                new_driver = new_node.driver_add(orig_driver.data_path, orig_driver.array_index) if orig_driver.array_index > 0 else new_node.driver_add(orig_driver.data_path)
                            except TypeError:
                                print('DATAPATH NOT FOUND: {} -> {}'.format(new_node['__orig_name__'], orig_driver.data_path))
                                continue
                            new_driver.driver.expression = orig_driver.driver.expression
                            new_driver.driver.type = orig_driver.driver.type
                            new_driver.driver.use_self = orig_driver.driver.use_self
                            for orig_var in orig_driver.driver.variables:
                                new_var = new_driver.driver.variables.new()
                                new_var.type = orig_var.type
                                new_var.name = orig_var.name

                                for var_index in range(0, len(orig_var.targets)):
                                    new_var.targets[var_index].data_path = orig_var.targets[var_index].data_path
                                    #new_var.targets[var_index].id_type = orig_var.targets[var_index].id_type

                                    orig_id = orig_var.targets[var_index].id

                                    new_id = next(obj for obj in new_nodes if obj['__orig_name__'] == orig_id['__orig_name__'])
                                    new_var.targets[var_index].id = new_id
                                    new_var.targets[var_index].bone_target = orig_var.targets[var_index].bone_target
                                    new_var.targets[var_index].transform_space = orig_var.targets[var_index].transform_space
                                    new_var.targets[var_index].transform_type = orig_var.targets[var_index].transform_type

                # TODO: import textures from linked files aswell

                exportable_nodes = [x for x in new_nodes if '__do_export__' not in x or x['__do_export__'] == 1]

                # remove helper from export
                bundle_info['empties'].pop(i)

                bundle_info['meshes'].extend(x for x in exportable_nodes if x.type in settings.mesh_types)
                bundle_info['empties'].extend(x for x in exportable_nodes if x.type in settings.empty_types)
                bundle_info['armatures'].extend(x for x in exportable_nodes if x.type in settings.armature_types)
