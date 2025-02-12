# SPDX-FileCopyrightText: 2011 Campbell Barton
#
# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
import functools
import os


def get_comparison(left, right):
    if left[0] > right[0]:
        return 1
    if left[0] < right[0]:
        return -1
    return 0


def get_sorting(array):
    sorting = sorted(array, key=functools.cmp_to_key(get_comparison))
    return list(sorting)


def get_weighting(vertices, group):
    index = group.index
    for i, v in enumerate(vertices):
        for g in v.groups:
            if g.group == index:
                yield (i, g.weight)
                break


def write_skin(obj, file, bone_weight_limit):
    mesh = obj.data
    groups = obj.vertex_groups
    vertices = mesh.vertices
    names = []
    skin = {}
    for i, group in enumerate(groups):
        name = group.name
        names.append(name)
        weighting = list(get_weighting(vertices, group))
        for j in range(len(weighting)):
            if not (weighting[j][0] in skin):
                skin[weighting[j][0]] = {}
            skin[weighting[j][0]][i] = weighting[j][1]
    vertices = get_sorting(list(enumerate(vertices)))
    for vertex, _ in vertices:
        if not (vertex in skin):
            continue
        weights = skin[vertex]
        temp = []
        for key in weights:
            temp.append([weights[key], key])
        temp = list(reversed(get_sorting(temp)))
        if bone_weight_limit > -1 and len(temp) > bone_weight_limit:
            temp = temp[:bone_weight_limit]
        total = 0.0
        for i in range(len(temp)):
            total += temp[i][0]
        if total < 1.0:
            total = 1.0 - total
            total /= float(len(temp))
            for i in range(len(temp)):
                temp[i][0] += total
        weights = {}
        for i in range(len(temp)):
            weights[temp[i][1]] = temp[i][0]
        file.write("vw " + str(vertex + 1))
        for key in weights:
            file.write(" %s %.6f" % (names[key], weights[key]))
        file.write("\n")


def write_qbo(
        context,
        filepath,
        frame_start,
        frame_end,
        root_transform_only=False,
        sort_child_names=True,
        bone_weight_limit=4,
):

    from mathutils import Matrix, Quaternion

    file = open(filepath, "w", encoding="utf8", newline="\n")

    obj = context.object
    arm = obj.data

    # Build a dictionary of children.
    # None for parentless
    children = {None: []}

    # initialize with blank lists
    for bone in arm.bones:
        children[bone.name] = []

    # keep bone order from armature, not esspential but means
    # we can maintain order from import -> export which secondlife incorrectly expects.
    for bone in arm.bones:
        children[getattr(bone.parent, "name", None)].append(bone.name)
    if sort_child_names:
        for key in children:
            children[key].sort()

    # bone name list in the order that the bones are written
    serialized_names = []

    node_locations = {}

    arm.transform(obj.matrix_world)
    #obj.matrix_world = Matrix()

    file.write("HIERARCHY %s\n" % obj.name)

    def write_recursive_nodes(bone_name, indent):
        my_children = children[bone_name]

        indent_str = "\t" * indent

        bone = arm.bones[bone_name]
        pose_bone = obj.pose.bones[bone_name]
        rot = bone.matrix.to_quaternion()
        loc = bone.head_local
        node_locations[bone_name] = loc
        # make relative if we can
        if bone.parent:
            loc = loc - node_locations[bone.parent.name]
        loc = list(loc)
        loc = loc[:min(3, len(loc))]
        while len(loc) < 3:
            loc.append(0.0)
        loc = tuple(loc)

        if indent:
            file.write("%sJOINT %s\n" % (indent_str, bone_name))
        else:
            file.write("%sROOT %s\n" % (indent_str, bone_name))

        file.write("%s{\n" % indent_str)
        file.write("%s\tOFFSET %.6f %.6f %.6f\n" % (indent_str, *loc))
        file.write("%s\tORIENT %.6f %.6f %.6f %.6f\n" % (indent_str, rot.x, rot.y, rot.z, rot.w))
        if (bone.use_connect or root_transform_only) and bone.parent:
            file.write("%s\tCHANNELS 4 Xrotation Yrotation Zrotation Wrotation\n" % indent_str)
        else:
            file.write("%s\tCHANNELS 7 Xposition Yposition Zposition Xrotation Yrotation Zrotation Wrotation\n" % indent_str)

        if my_children:
            # store the location for the children
            # to get their relative offset

            # Write children
            for child_bone in my_children:
                serialized_names.append(child_bone)
                write_recursive_nodes(child_bone, indent + 1)

        else:
            # Write the bone end.
            file.write("%s\tEnd Site\n" % indent_str)
            file.write("%s\t{\n" % indent_str)
            loc = bone.tail_local - node_locations[bone_name]
            loc = list(loc)
            loc = loc[:min(3, len(loc))]
            while len(loc) < 3:
                loc.append(0.0)
            loc = tuple(loc)
            file.write("%s\t\tOFFSET %.6f %.6f %.6f\n" % (indent_str, *loc))
            file.write("%s\t\tORIENT %.6f %.6f %.6f %.6f\n" % (indent_str, rot.x, rot.y, rot.z, rot.w))
            file.write("%s\t}\n" % indent_str)

        file.write("%s}\n" % indent_str)

    if len(children[None]) == 1:
        key = children[None][0]
        serialized_names.append(key)
        indent = 0

        write_recursive_nodes(key, indent)

    else:
        # Write a dummy parent node, with a dummy key name
        # Just be sure it's not used by another bone!
        i = 0
        key = "__%d" % i
        while key in children:
            i += 1
            key = "__%d" % i
        file.write("ROOT %s\n" % key)
        file.write("{\n")
        file.write("\tOFFSET 0.0 0.0 0.0\n")
        file.write("\tORIENT 0.0 0.0 0.0 1.0\n")
        file.write("\tCHANNELS 0\n")  # Xposition Yposition Zposition Xrotation Yrotation Zrotation Wrotation
        indent = 1

        # Write children
        for child_bone in children[None]:
            serialized_names.append(child_bone)
            write_recursive_nodes(child_bone, indent)

        file.write("}\n")

    # redefine bones as sorted by serialized_names
    # so we can write motion

    class DecoratedBone:
        __slots__ = (
            # Bone name, used as key in many places.
            "name",
            "parent",  # decorated bone parent, set in a later loop
            # Blender armature bone.
            "rest_bone",
            # Blender pose bone.
            "pose_bone",
            # Blender pose matrix.
            "pose_mat",
            # Blender rest matrix (armature space).
            "rest_arm_mat",
            # Blender rest matrix (local space).
            "rest_local_mat",
            # Pose_mat inverted.
            "pose_imat",
            # Rest_arm_mat inverted.
            "rest_arm_imat",
            # Rest_local_mat inverted.
            "rest_local_imat",
            # Is the bone disconnected to the parent bone?
            "skip_position",
        )

        def __init__(self, bone_name):
            self.name = bone_name
            self.rest_bone = arm.bones[bone_name]
            self.pose_bone = obj.pose.bones[bone_name]

            self.pose_mat = self.pose_bone.matrix

            # mat = self.rest_bone.matrix  # UNUSED
            self.rest_arm_mat = self.rest_bone.matrix_local
            self.rest_local_mat = self.rest_bone.matrix

            # inverted mats
            self.pose_imat = self.pose_mat.inverted()
            self.rest_arm_imat = self.rest_arm_mat.inverted()
            self.rest_local_imat = self.rest_local_mat.inverted()

            self.parent = None
            self.skip_position = ((self.rest_bone.use_connect or root_transform_only) and self.rest_bone.parent)

        def update_posedata(self):
            self.pose_mat = self.pose_bone.matrix
            self.pose_imat = self.pose_mat.inverted()

        def __repr__(self):
            if self.parent:
                return "[\"%s\" child on \"%s\"]\n" % (self.name, self.parent.name)
            else:
                return "[\"%s\" root bone]\n" % (self.name)

    bones_decorated = [DecoratedBone(bone_name) for bone_name in serialized_names]

    # Assign parents
    bones_decorated_dict = {dbone.name: dbone for dbone in bones_decorated}
    for dbone in bones_decorated:
        parent = dbone.rest_bone.parent
        if parent:
            dbone.parent = bones_decorated_dict[parent.name]
    del bones_decorated_dict
    # finish assigning parents

    scene = context.scene
    frame_current = scene.frame_current

    file.write("MOTION animation_0\n")
    file.write("Frames: %d\n" % (frame_end - frame_start + 1))
    file.write("Frame Time: %.6f\n" % (1.0 / (scene.render.fps / scene.render.fps_base)))

    for frame in range(frame_start, frame_end + 1):
        scene.frame_set(frame)

        for dbone in bones_decorated:
            dbone.update_posedata()

        for dbone in bones_decorated:
            trans = Matrix.Translation(dbone.rest_bone.head_local)
            itrans = Matrix.Translation(-dbone.rest_bone.head_local)

            if dbone.parent:
                mat_final = dbone.parent.rest_arm_mat @ dbone.parent.pose_imat @ dbone.pose_mat @ dbone.rest_arm_imat
                mat_final = itrans @ mat_final @ trans
                loc = mat_final.to_translation() + (dbone.rest_bone.head_local - dbone.parent.rest_bone.head_local)
            else:
                mat_final = dbone.pose_mat @ dbone.rest_arm_imat
                mat_final = itrans @ mat_final @ trans
                loc = mat_final.to_translation() + dbone.rest_bone.head

            rot = mat_final.to_quaternion()
            loc = list(loc)
            loc = loc[:min(3, len(loc))]
            while len(loc) < 3:
                loc.append(0.0)

            if not dbone.skip_position:
                file.write("%.6f %.6f %.6f " % (loc[0], loc[1], loc[2]))

            file.write(
                "%.6f %.6f %.6f %.6f " % (
                    rot.x,
                    rot.y,
                    rot.z,
                    rot.w,
                )
            )

        file.write("\n")

    file.write("\n\n")
    try:
        bpy.ops.wm.obj_export(filepath=filepath + ".obj")
    except:
        bpy.ops.export_scene.obj(filepath=filepath + ".obj")
    wav = open(filepath + ".obj", "r", encoding="utf8", newline="\n")
    lines = wav.readlines()
    wav.close()
    for line in lines:
        file.write(line.strip() + "\n")
        for wav in bpy.data.objects:
            if wav.parent == obj and wav.type == "MESH" and line.strip() == "o " + wav.name:
                write_skin(wav, file, bone_weight_limit)
    try:
        os.remove(filepath + ".obj")
    except:
        pass

    file.close()

    scene.frame_set(frame_current)

    print("QBO Exported: %s frames:%d\n" % (filepath, frame_end - frame_start + 1))


def save(
        context, filepath="",
        frame_start=-1,
        frame_end=-1,
        root_transform_only=False,
        sort_child_names=True,
        bone_weight_limit=4,
):
    write_qbo(
        context, filepath,
        frame_start=frame_start,
        frame_end=frame_end,
        root_transform_only=root_transform_only,
        sort_child_names=sort_child_names,
        bone_weight_limit=bone_weight_limit,
    )

    return {'FINISHED'}
