import bpy
import tempfile
from pathlib import Path


class DemBonesProperties(bpy.types.PropertyGroup):
    n_bones: bpy.props.IntProperty(
        name="nBones",
        description="Number of bones",
    )
    n_init_iters: bpy.props.IntProperty(
        name="nInitIters",
        description="Number iterations per init cluster splitting",
        default=10,
    )
    n_iters: bpy.props.IntProperty(
        name="nIters",
        description="Number of global iterations",
        default=100,
    )
    tolerance: bpy.props.FloatProperty(
        name="tolerance",
        description="Convergence tolerance, stop if error relatively reduces less than \
     [--tolerance] in [--patience] consecutive iterations",
        default=0.001,
    )
    patience: bpy.props.IntProperty(
        name="patience",
        description="Convergence patience, stop if error relatively reduces less than \
     [--tolerance] in [--patience] consecutive iterations",
        default=3,
    )
    n_trans_iters: bpy.props.IntProperty(
        name="nTransIters",
        description="Number of transformation update iterations per global iteration",
        default=5,
    )
    bind_update: bpy.props.IntProperty(
        name="bindUpdate",
        description="Update bind pose (0=no update, 1=update joint positions, 2=regroup \
     joints under one root)",
        default=1,
    )
    trans_affine: bpy.props.FloatProperty(
        name="transAffine",
        description="Bone translations affinity soft constraint",
        default=10,
    )
    trans_affine_norm: bpy.props.FloatProperty(
        name="transAffineNorm",
        description="p-Norm for bone translations affinity",
        default=4,
    )
    n_weights_iters: bpy.props.IntProperty(
        name="nWeightsIters",
        description="Number of weights update iterations per global iteration",
        default=3,
    )
    nnz: bpy.props.IntProperty(
        name="nnz",
        description="Number of non-zero weights per vertex",
        default=8,
    )
    weights_smooth: bpy.props.FloatProperty(
        name="weightsSmooth",
        description="Weights smoothness soft constraint",
        default=0.0001,
    )
    weights_smooth_step: bpy.props.FloatProperty(
        name="weightsSmoothStep",
        description="Step size for the weights smoothness",
        default=1,
    )
    info_msg: bpy.props.StringProperty(
        name="info_msg",
        description="Print message"
    )

    def register():
        bpy.types.Scene.dembones = bpy.props.PointerProperty(type=DemBonesProperties)
