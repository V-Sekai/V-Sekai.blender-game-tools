# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name" : "Mesh Materializer",
    "author" : "Mark Kingsnorth",
    "description" : "Paint new object geometry based on a target object UV map",
    "blender" : (2, 82, 0),
    "version" : (2, 0, 0),
    "location" : "View3D",
    "warning" : "",
    "category" : "Add Mesh"
}

import bpy

from . operators import (MeshMaterializer_OT_Operator, 
                            MeshMaterializer_OT_ModalOperator,
                            MeshMaterializerAddSceneObj_OT_Operator, 
                            MeshMaterializerAddSceneCollection_OT_Operator,
                            MeshMaterializerRemoveSceneObj_OT_Operator,
                            MeshMaterializerRemoveSceneObjFromCol_OT_Operator,
                            MeshMaterializerRemoveCollectionObj_OT_Operator,
                            MeshMaterializerDissolveGeom_OT_Operator,
                            MeshMaterializerRemoveDoubles_OT_Operator,
                            MeshMaterializerFillHoles_OT_Operator,
                            MeshMaterializerRecalcNormals_OT_Operator,
                            MeshMaterializerDeleteSelection_OT_Operator,
                            MeshMaterializerRemoveCutObjects_OT_Operator,
                            MeshMaterializerConfirm_OT_Operator,
                            MESH_OT_AddMeshMatGeoNodesOperator,
                            OBJECT_MT_mesh_mat,
                            menu_func,
                            meshmat_quick_func)

from . ui import (MeshMaterializer_PT_Panel,
                    MeshMaterializer_PT_GeneralPanel,
                    MeshMaterializer_PT_ObjectsPanel,
                    MeshMaterializer_PT_OperatorsPanel,
                    MeshMaterializer_PT_AdvancedPanel)
from . tools import (MeshMaterializerTool, MeshMaterializerToolEdit)
from . import props
from typing import Optional
import bpy.utils.previews
import os
from . preferences import MeshMaterializerAddonPreferences




class MeshMaterializerSourceCollection(bpy.types.PropertyGroup):
    """A class representing the properties of a collection of objects for the mesh material."""
    name : bpy.props.StringProperty(name="Name", default="Unknown")
    is_enabled : bpy.props.BoolProperty(name="Enabled", default=True)
    source_objects : bpy.props.CollectionProperty(
        type=props.MeshMaterializerSourceObject
    )
            
# Load all classes.
classes = (props.MeshMaterializerSourceObject,
            MeshMaterializerSourceCollection,
            MeshMaterializer_OT_Operator,
            MeshMaterializer_OT_ModalOperator,
            MeshMaterializerAddSceneObj_OT_Operator,
            MeshMaterializerAddSceneCollection_OT_Operator,
            MeshMaterializerRemoveSceneObj_OT_Operator,
            MeshMaterializerRemoveSceneObjFromCol_OT_Operator,
            MeshMaterializerRemoveCollectionObj_OT_Operator,
            MeshMaterializerDissolveGeom_OT_Operator,
            MeshMaterializerRemoveDoubles_OT_Operator,
            MeshMaterializerFillHoles_OT_Operator,
            MeshMaterializerRecalcNormals_OT_Operator,
            MeshMaterializerDeleteSelection_OT_Operator,
            MeshMaterializerRemoveCutObjects_OT_Operator,
            MeshMaterializerConfirm_OT_Operator,
            MeshMaterializer_PT_Panel,
            MeshMaterializer_PT_OperatorsPanel,
            MeshMaterializer_PT_ObjectsPanel,
            MeshMaterializer_PT_GeneralPanel,
            MeshMaterializer_PT_AdvancedPanel,
            MeshMaterializerAddonPreferences,
            MESH_OT_AddMeshMatGeoNodesOperator,
            OBJECT_MT_mesh_mat
            )

def scene_chosenobject_poll(self, object):
    """Filters the object chooser."""
    return object.type == 'MESH'


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.VIEW3D_MT_editor_menus.append(meshmat_quick_func)

    bpy.types.VIEW3D_MT_object.append(menu_func)
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)

    # Declare scene properties to be persisted.
    bpy.types.Scene.mesh_mat_object_to_add = bpy.props.PointerProperty(
        type=bpy.types.Object,
        poll=scene_chosenobject_poll
    )

    bpy.types.Scene.mesh_mat_collection_to_add = bpy.props.PointerProperty(
        type=bpy.types.Collection
    )

    bpy.types.Scene.mesh_mat_random_seed = bpy.props.IntProperty(
            name="Random Seed",
            description="Random Seed to create object pattern",
            min=0,
            default=123456,
            update=props.exec_interactive
        )

    bpy.types.Scene.mesh_mat_source_objects = bpy.props.CollectionProperty(
        type=props.MeshMaterializerSourceObject
    )

    bpy.types.Scene.mesh_mat_source_collections = bpy.props.CollectionProperty(
        type=MeshMaterializerSourceCollection
    )

    bpy.types.Scene.mesh_mat_tiles_across = bpy.props.IntProperty(
            name="Tiles Across",
            description="Number of object tiles across",
            default=10,
            min=1,
            update=props.exec_interactive
        )

    bpy.types.Scene.mesh_mat_tiles_down = bpy.props.IntProperty(
            name="Tiles Down",
            description="Number of object tiles down",
            default=10,
            min=1,
            update=props.exec_interactive
        )

    bpy.types.Scene.mesh_mat_pattern_type = bpy.props.EnumProperty(
                                items= props.pattern_items,
                                name = "Pattern Type", default='0',
                                update=props.exec_interactive
                                )

    bpy.types.Scene.mesh_mat_approach = bpy.props.EnumProperty(
                                items= props.approach_items,
                                name = "Approach", default='0',
                                update=props.exec_interactive
                                )

    bpy.types.Scene.mesh_mat_add_edge_split = bpy.props.BoolProperty(
                                name="Edge Split",
                                default=True,
                                description="Add an edge split modifier to generated mesh to clean up geometry.",
                                update=props.exec_interactive)

    # General source object parameters.
    bpy.types.Scene.mesh_mat_randomize_parameters = bpy.props.BoolProperty(name="Randomize", default=False, update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_randomize_parameters_seed = bpy.props.IntProperty(
            name="Randomize Seed",
            description="Random Seed for object parameters",
            min=0,
            default=654321,
            update=props.exec_interactive
        )
    bpy.types.Scene.mesh_mat_location = bpy.props.FloatVectorProperty(name="Location", default=[0,0,0], precision=4, subtype='XYZ', update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_scale_x = bpy.props.FloatProperty(name="Scale X", default=1, min=0, precision=4, update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_scale_y = bpy.props.FloatProperty(name="Scale Y", default=1, min=0, precision=4, update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_scale_z = bpy.props.FloatProperty(name="Scale Z", default=1, min=0, precision=4, update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_rotate = bpy.props.FloatVectorProperty(name="Rotate", default=[0,0,0], precision=4, subtype="EULER", update=props.exec_interactive)
    
    bpy.types.Scene.mesh_mat_location_rand = bpy.props.FloatVectorProperty(name="Location", default=[0,0,0], precision=4, subtype='XYZ', update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_scale_x_rand = bpy.props.FloatProperty(name="+/-", default=0, min=0, precision=2, update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_scale_y_rand = bpy.props.FloatProperty(name="+/-", default=0, min=0, precision=2, update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_scale_z_rand = bpy.props.FloatProperty(name="+/-", default=0, min=0, precision=2, update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_rotate_rand = bpy.props.FloatVectorProperty(name="+/-", default=[0,0,0], precision=4, subtype="EULER", update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_maintain_proportions = bpy.props.BoolProperty(name="Maintain Aspect Ratio", default=False, update=props.exec_interactive)

    bpy.types.Scene.mesh_mat_align_normal = bpy.props.BoolProperty(name="Normal Alignment", default=True, update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_align_normal_type = bpy.props.EnumProperty(
                                items= props.align_normal_type_items,
                                name = "Normal alignment", default='1', 
                                update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_normal_height = bpy.props.FloatProperty(name="Height", default=1.0, precision=4, update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_obj_pos = bpy.props.EnumProperty(
                                items= props.obj_pos_items,
                                name = "Position Object", default='0', 
                                update=props.exec_interactive)

    bpy.types.Scene.mesh_mat_custom_normal = bpy.props.FloatVectorProperty(
            name="Custom Normal",
            description="Custom upwards direction of object",
            subtype='XYZ',
            default=[0,0,1],
            min=-1,
            max=1,
            step=1,
            update=props.exec_interactive)
    bpy.types.Scene.mesh_mat_select_cut_geom = bpy.props.BoolProperty(name="Select Cut Geometry", default=True, update=props.exec_interactive)

    def update_function(self, context):
        if self.mesh_mat_toggle:
            bpy.ops.view3d.mesh_materializer_modal('INVOKE_REGION_WIN')
        return None

    bpy.types.Scene.mesh_mat_toggle = bpy.props.BoolProperty(
                                                                       default = False,
                                                                         update = update_function)
    bpy.types.Scene.mesh_mat_brush_size = bpy.props.FloatProperty(
            name="Brush Size",
            description="Size of surrounding brush",
            default=0.1,
            min=0,
            precision=4

        )

    bpy.types.Scene.mesh_mat_interactive_mode = bpy.props.BoolProperty(
                                name="Interactive Mode",
                                default=False,
                                description="Interactive Mode")

    # #register the tools.
    # TODO removed this for now as the toolkit seems to be buggy
    # bpy.utils.register_tool(MeshMaterializerTool, separator=True)
    # bpy.utils.register_tool(MeshMaterializerToolEdit, separator=True)

def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)
    
    bpy.types.VIEW3D_MT_editor_menus.remove(meshmat_quick_func)

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    # Remove the scene property references.
    del bpy.types.Scene.mesh_mat_random_seed
    del bpy.types.Scene.mesh_mat_source_objects
    del bpy.types.Scene.mesh_mat_source_collections
    del bpy.types.Scene.mesh_mat_object_to_add
    del bpy.types.Scene.mesh_mat_collection_to_add
    del bpy.types.Scene.mesh_mat_tiles_across
    del bpy.types.Scene.mesh_mat_tiles_down
    del bpy.types.Scene.mesh_mat_align_normal
    del bpy.types.Scene.mesh_mat_align_normal_type
    del bpy.types.Scene.mesh_mat_normal_height
    del bpy.types.Scene.mesh_mat_obj_pos
    del bpy.types.Scene.mesh_mat_location
    del bpy.types.Scene.mesh_mat_scale_x
    del bpy.types.Scene.mesh_mat_scale_y
    del bpy.types.Scene.mesh_mat_scale_z
    del bpy.types.Scene.mesh_mat_rotate
    del bpy.types.Scene.mesh_mat_location_rand
    del bpy.types.Scene.mesh_mat_scale_x_rand
    del bpy.types.Scene.mesh_mat_scale_y_rand
    del bpy.types.Scene.mesh_mat_scale_z_rand
    del bpy.types.Scene.mesh_mat_rotate_rand
    del bpy.types.Scene.mesh_mat_maintain_proportions
    del bpy.types.Scene.mesh_mat_approach
    del bpy.types.Scene.mesh_mat_custom_normal
    del bpy.types.Scene.mesh_mat_add_edge_split
    del bpy.types.Scene.mesh_mat_select_cut_geom
    del bpy.types.Scene.mesh_mat_randomize_parameters
    del bpy.types.Scene.mesh_mat_randomize_parameters_seed
    del bpy.types.Scene.mesh_mat_toggle
    del bpy.types.Scene.mesh_mat_brush_size