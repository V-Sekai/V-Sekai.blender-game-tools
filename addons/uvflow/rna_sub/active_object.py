from uvflow.addon_utils import Register
from uvflow.props.mesh import MeshProps
from uvflow.globals import print_debug

from bpy.types import LayerObjects, Context, Object, Mesh


last_mesh_id: int = 0


@Register.RNA_SUB(LayerObjects, 'active', persistent=True, data_path='view_layer.objects')
def on_active_object_change(context: Context, view_layer_objects: LayerObjects, active_object: Object):
    if active_object.type != 'MESH':
        return

    print(f"RNA::on_active_object_change -> '{active_object.name}'")
    act_mesh: Mesh = active_object.data

    # Initialize/Ensure UVMap MeshProps.
    # Needed for UVMap callbacks (switch, rename, add, remove).
    global last_mesh_id
    act_mesh_id = act_mesh.as_pointer()
    if last_mesh_id != act_mesh_id:
        last_mesh_id = act_mesh_id
        MeshProps.ensure_last_uv_layer(act_mesh)
