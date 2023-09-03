from uvflow.addon_utils import Register
from uvflow.props.mesh import MeshProps
from uvflow.prefs import UVFLOW_Preferences
from uvflow.addon_utils.utils.mode import CM_ModeToggle
from uvflow.tool.attributes import save_attributes, apply_attributes
from uvflow.operators.op_geo_overlay import set_seam_props
from uvflow.operators.op_checker import update_material_uvmap

from bpy.types import Context, MeshUVLoopLayer, UVLoopLayers, Mesh, Object


@Register.RNA_SUB(Object, 'mode', persistent=True)
def on_mode_change(context: Context, object: Object, mode: str):
    print(f"RNA::on_mode_change -> {mode} ['{object.name}']")
    pass
