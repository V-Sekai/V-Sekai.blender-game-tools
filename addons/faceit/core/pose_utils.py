from mathutils import Matrix
from math import degrees


def reset_pose(rig):
    '''Reset a rig to rest pose'''
    for pb in rig.pose.bones:
        reset_pb(pb)


def reset_pb(pb, reset_location=True, reset_rotation=True, reset_scale=True):
    '''Reset a pose bone to bind transforms'''
    M = pb.matrix_basis
    I = Matrix()
    if M == I:
        return
    loc, rot, scale = M.decompose()
    T = I if reset_location else Matrix.Translation(loc)
    R = I if reset_rotation else rot.to_matrix().to_4x4()
    S = I if reset_scale else Matrix.Diagonal(scale.to_4d())
    pb.matrix_basis = T @ R @ S


def is_pb_in_rest_pose(pb):
    '''Check if a pose bone is in rest pose'''
    return pb.matrix_basis == Matrix()  # pb.bone.matrix_local


def get_edit_bone_roll(pb):
    '''Get the edit bone roll from pose bone'''
    b = pb.bone
    _axis, angle = b.AxisRollFromMatrix(b.matrix, axis=pb.y_axis)
    return degrees(angle)


def copy_pose_bone_constraints(src_pb, dst_pb):
    '''Copy constraints from one pose bone to another'''
    for c_src in src_pb.constraints:
        c_dst = dst_pb.constraints.get(c_src.name)
        if not c_dst:
            c_dst = dst_pb.constraints.new(c_src.type)
        # collect names of writable properties
        properties = [p.identifier for p in c_src.bl_rna.properties if not p.is_readonly]
        # copy those properties
        for prop in properties:
            if prop == 'target':
                target_obj = c_src.target
                if target_obj == c_src.id_data:
                    c_dst.target = dst_pb.id_data
            else:
                setattr(c_dst, prop, getattr(c_src, prop))
        


# def copy_constraints(source, target):
#     """ Copy constraints from source to target """
#     for source_constraint in source.constraints:
#         target_constraint = target.constraints.new(type=source_constraint.type)
#         for attr in dir(source_constraint):
#             if not attr.startswith("_") and attr != "type" and not callable(getattr(source_constraint, attr)):
#                 setattr(target_constraint, attr, getattr(source_constraint, attr))


def remove_all_pose_bone_constraints(pb):
    '''Remove all constraints from a pose bone'''
    for c in pb.constraints:
        pb.constraints.remove(c)


def copy_pose_bone_data(src_pb, dst_pb):
    # Copy properties
    for prop in dir(src_pb):
        # Exclude methods and special properties
        if not prop.startswith('__') and not callable(getattr(src_pb, prop)):
            try:
                setattr(dst_pb, prop, getattr(src_pb, prop))
            except:
                # print('Cannot copy property: %s' % prop)
                # In case the property cannot be set, pass
                pass


def copy_pose_bone_properties(src_pb, dst_pb, copy_name=False):
    '''Copy properties from one pose bone to another'''
    # collect names of writable properties
    properties = [p.identifier for p in src_pb.bl_rna.properties if not p.is_readonly]
    if not copy_name:
        properties.remove('name')
    # copy those properties
    for prop in properties:
        setattr(dst_pb, prop, getattr(src_pb, prop))

def save_pose(rig):
    '''Save the matrices of all pose bones in a pose dict'''
    pose = {}
    for pb in rig.pose.bones:
        pose[pb.name] = pb.matrix_basis.copy()
    return pose


def restore_saved_pose(rig, pose):
    '''Restore the matrices of all pose bones from a pose dict'''
    for pb in rig.pose.bones:
        if pb.name in pose:
            pb.matrix_basis = pose[pb.name]
