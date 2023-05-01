import bpy
dembones = bpy.context.scene.dembones

dembones.n_bones = 0
dembones.n_init_iters = 10
dembones.n_iters = 100
dembones.tolerance = 0.0010000000474974513
dembones.patience = 3
dembones.n_trans_iters = 5
dembones.bind_update = 1
dembones.trans_affine = 10.0
dembones.trans_affine_norm = 4.0
dembones.n_weights_iters = 3
dembones.nnz = 8
dembones.weights_smooth = 9.999999747378752e-05
dembones.weights_smooth_step = 1.0
dembones.dbg = 0
dembones.intermediate_files = '/tmp'
dembones.log = '/tmp/blender_dembones.txt'
