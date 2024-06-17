# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

bl_info = {
    "name": "Voxel Heat Diffuse Skinning",
    "author": "mesh online",
    "version": (3, 5, 3),
    "blender": (2, 80, 0),
    "location": "File > Import-Export | View3D > UI > Mesh Online",
    "description": "Voxel skinning toolset",
    "warning": "",
    "wiki_url": "http://www.mesh-online.net/vhd.html",
    "category": "Import-Export | Object",
    }


if "bpy" in locals():
    import importlib
    if "joint_alignment_tool" in locals():
        importlib.reload(joint_alignment_tool)
    if "surface_heat_diffuse_skinning" in locals():
        importlib.reload(surface_heat_diffuse_skinning)
    if "voxel_heat_diffuse_export_bone" in locals():
        importlib.reload(voxel_heat_diffuse_export_bone)
    if "voxel_heat_diffuse_export_mesh" in locals():
        importlib.reload(voxel_heat_diffuse_export_mesh)
    if "voxel_heat_diffuse_import_weight" in locals():
        importlib.reload(voxel_heat_diffuse_import_weight)
    if "voxel_heat_diffuse_skinning" in locals():
        importlib.reload(voxel_heat_diffuse_skinning)
    if "corrective_smooth_baker" in locals():
        importlib.reload(corrective_smooth_baker)


def register():
    from .joint_alignment_tool import register_joint_alignment_tool
    register_joint_alignment_tool()
    from .surface_heat_diffuse_skinning import register_surface_heat_diffuse_skinning
    register_surface_heat_diffuse_skinning()
    from .voxel_heat_diffuse_export_bone import register_voxel_heat_diffuse_export_bone
    register_voxel_heat_diffuse_export_bone()
    from .voxel_heat_diffuse_export_mesh import register_voxel_heat_diffuse_export_mesh
    register_voxel_heat_diffuse_export_mesh()
    from .voxel_heat_diffuse_import_weight import register_voxel_heat_diffuse_import_weight
    register_voxel_heat_diffuse_import_weight()
    from .voxel_heat_diffuse_skinning import register_voxel_heat_diffuse_skinning
    register_voxel_heat_diffuse_skinning()
    from .corrective_smooth_baker import register_corrective_smooth_baker
    register_corrective_smooth_baker()


def unregister():
    from .joint_alignment_tool import unregister_joint_alignment_tool
    unregister_joint_alignment_tool()
    from .surface_heat_diffuse_skinning import unregister_surface_heat_diffuse_skinning
    unregister_surface_heat_diffuse_skinning()
    from .voxel_heat_diffuse_export_bone import unregister_voxel_heat_diffuse_export_bone
    unregister_voxel_heat_diffuse_export_bone()
    from .voxel_heat_diffuse_export_mesh import unregister_voxel_heat_diffuse_export_mesh
    unregister_voxel_heat_diffuse_export_mesh()
    from .voxel_heat_diffuse_import_weight import unregister_voxel_heat_diffuse_import_weight
    unregister_voxel_heat_diffuse_import_weight()
    from .voxel_heat_diffuse_skinning import unregister_voxel_heat_diffuse_skinning
    unregister_voxel_heat_diffuse_skinning()
    from .corrective_smooth_baker import unregister_corrective_smooth_baker
    unregister_corrective_smooth_baker()
