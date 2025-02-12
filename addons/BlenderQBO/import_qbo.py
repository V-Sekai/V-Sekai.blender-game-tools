# SPDX-FileCopyrightText: 2011 Campbell Barton
#
# SPDX-License-Identifier: GPL-2.0-or-later

from math import radians, ceil

import logging
import json
import time
import bpy
from datetime import datetime
from bpy.app.translations import pgettext_tip as tip_
from mathutils import Vector, Quaternion, Matrix


EPSILON = 0.001


class QBO_Node:
    __slots__ = (
        # QBO joint name.
        'name',
        # QBO_Node type or None for no parent.
        'parent',
        # A list of children of this type..
        'children',
        # Worldspace rest location for the head of this node.
        'rest_head_world',
        # Localspace rest location for the head of this node.
        'rest_head_local',
        # Worldspace rest location for the tail of this node.
        'rest_tail_world',
        # Worldspace rest location for the tail of this node.
        'rest_tail_local',
        # List of 7 ints, -1 for an unused channel,
        # otherwise an index for the QBO motion data lines,
        # loc triple then rot triple.
        'channels',
        # A list one tuple's one for each frame: (locx, locy, locz, rotx, roty, rotz, rotw),
        'anim_data',
        # Convenience function, bool.
        'has_loc',
        # Convenience function, bool.
        'has_rot',
        # Index from the file, not strictly needed but nice to maintain order.
        'index',
        # Use this for whatever you want.
        'temp',
    )

    def __init__(self, name, rest_head_world, rest_head_local, parent, channels, index):
        self.name = name
        self.rest_head_world = rest_head_world
        self.rest_head_local = rest_head_local
        self.rest_tail_world = None
        self.rest_tail_local = None
        self.parent = parent
        self.channels = channels
        self.index = index

        # convenience functions
        self.has_loc = channels[0] != -1 or channels[1] != -1 or channels[2] != -1
        self.has_rot = channels[3] != -1 or channels[4] != -1 or channels[5] != -1 or channels[6] != -1

        self.children = []

        # List of 7 length tuples: (lx, ly, lz, rx, ry, rz, rw)
        # even if the channels aren't used they will just be zero.
        self.anim_data = [(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)]

    def __repr__(self):
        return (
            "QBO name: '%s', rest_loc:(%.3f,%.3f,%.3f), rest_tail:(%.3f,%.3f,%.3f)" % (
                self.name,
                *self.rest_head_world,
                *self.rest_head_world,
            )
        )


def sorted_nodes(qbo_nodes):
    qbo_nodes_list = list(qbo_nodes.values())
    qbo_nodes_list.sort(key=lambda qbo_node: qbo_node.index)
    return qbo_nodes_list


def get_distance(left, right):
    distance = 0.0
    for i in range(min(len(left), len(right))):
        distance += (left[i]-right[i])**2.0
    return distance**0.5


def read_qbo(logger, context, file_path):
    # File loading stuff
    # Open the file for importing
    file = open(file_path, 'r')

    # Separate into a list of lists, each line a list of words.
    file_lines = file.readlines()
    # Non standard carriage returns?
    if len(file_lines) == 1:
        file_lines = file_lines[0].split('\r')

    # Split by whitespace.
    file_lines = [ll for ll in [l.split() for l in file_lines]]

    # Create hierarchy as empties
    if file_lines[0][0].lower() == 'hierarchy':
        logger.debug('Importing the QBO Hierarchy for: ' + file_path)
        pass
    else:
        raise Exception("This is not a QBO file")

    qbo_nodes = {None: None}
    qbo_nodes_serial = [None]
    qbo_frame_count = None
    qbo_frame_time = None

    channelIndex = -1

    lineIdx = 0  # An index for the file.
    while lineIdx < len(file_lines) - 1:
        if file_lines[lineIdx][0].lower() in {'root', 'joint'}:

            # Join spaces into 1 word with underscores joining it.
            if len(file_lines[lineIdx]) > 2:
                file_lines[lineIdx][1] = '_'.join(file_lines[lineIdx][1:])
                file_lines[lineIdx] = file_lines[lineIdx][:2]

            # MAY NEED TO SUPPORT MULTIPLE ROOTS HERE! Still unsure weather multiple roots are possible?

            # Make sure the names are unique - Object names will match joint names exactly and both will be unique.
            name = file_lines[lineIdx][1]

            # While unlikely, there exists a user report of duplicate joint names, see: #109399.
            if name in qbo_nodes:
                name_orig = name
                name_index = 1
                while (name := "%s.%03d" % (name_orig, name_index)) in qbo_nodes:
                    name_index += 1
                del name_orig, name_index

            logger.debug('%snode: %s, parent: %s' % (len(qbo_nodes_serial) * '  ', name,  qbo_nodes_serial[-1]))

            lineIdx += 2  # Increment to the next line (Offset)
            rest_head_local = Vector((
                float(file_lines[lineIdx][1]),
                float(file_lines[lineIdx][2]),
                float(file_lines[lineIdx][3]),
            ))
            lineIdx += 2  # Increment to the next line, skipping past the Orientation for now (Channels)

            # newChannel[Xposition, Yposition, Zposition, Xrotation, Yrotation, Zrotation, Wrotation]
            # newChannel references indices to the motiondata,
            # if not assigned then -1 refers to the last value that will be added on loading at a value of zero, this is appended
            # We'll add a zero value onto the end of the MotionDATA so this always refers to a value.
            my_channel = [-1, -1, -1, -1, -1, -1, -1]
            for channel in file_lines[lineIdx][2:]:
                channel = channel.lower()
                channelIndex += 1  # So the index points to the right channel
                if channel == 'xposition':
                    my_channel[0] = channelIndex
                elif channel == 'yposition':
                    my_channel[1] = channelIndex
                elif channel == 'zposition':
                    my_channel[2] = channelIndex

                elif channel == 'xrotation':
                    my_channel[3] = channelIndex
                elif channel == 'yrotation':
                    my_channel[4] = channelIndex
                elif channel == 'zrotation':
                    my_channel[5] = channelIndex
                elif channel == 'wrotation':
                    my_channel[6] = channelIndex

            channels = file_lines[lineIdx][2:]

            my_parent = qbo_nodes_serial[-1]  # account for none

            # Apply the parents offset accumulatively
            if my_parent is None:
                rest_head_world = Vector(rest_head_local)
            else:
                rest_head_world = my_parent.rest_head_world + rest_head_local

            qbo_node = qbo_nodes[name] = QBO_Node(
                name,
                rest_head_world,
                rest_head_local,
                my_parent,
                my_channel,
                len(qbo_nodes) - 1,
            )

            # If we have another child then we can call ourselves a parent, else
            qbo_nodes_serial.append(qbo_node)

        # Account for an end node.
        # There is sometimes a name after 'End Site' but we will ignore it.
        if file_lines[lineIdx][0].lower() == 'end' and file_lines[lineIdx][1].lower() == 'site':
            # Increment to the next line (Offset)
            lineIdx += 2
            rest_tail = Vector((
                float(file_lines[lineIdx][1]),
                float(file_lines[lineIdx][2]),
                float(file_lines[lineIdx][3]),
            ))
            lineIdx += 1  # Increment to the next line (Orientation)

            qbo_nodes_serial[-1].rest_tail_world = qbo_nodes_serial[-1].rest_head_world + rest_tail
            qbo_nodes_serial[-1].rest_tail_local = qbo_nodes_serial[-1].rest_head_local + rest_tail

            # Just so we can remove the parents in a uniform way,
            # the end has kids so this is a placeholder.
            qbo_nodes_serial.append(None)

        if len(file_lines[lineIdx]) == 1 and file_lines[lineIdx][0] == '}':  # == ['}']
            qbo_nodes_serial.pop()  # Remove the last item

        # End of the hierarchy. Begin the animation section of the file with
        # the following header.
        #  MOTION
        #  Frames: n
        #  Frame Time: dt
        if len(file_lines[lineIdx]) > 0 and file_lines[lineIdx][0].lower() == 'motion':
            lineIdx += 1  # Read frame count.
            if (
                    len(file_lines[lineIdx]) == 2 and
                    file_lines[lineIdx][0].lower() == 'frames:'
            ):
                qbo_frame_count = int(file_lines[lineIdx][1])

            lineIdx += 1  # Read frame rate.
            if (
                    len(file_lines[lineIdx]) == 3 and
                    file_lines[lineIdx][0].lower() == 'frame' and
                    file_lines[lineIdx][1].lower() == 'time:'
            ):
                qbo_frame_time = float(file_lines[lineIdx][2])

            lineIdx += 1  # Set the cursor to the first frame

            break

        lineIdx += 1

    # Remove the None value used for easy parent reference
    del qbo_nodes[None]
    # Don't use anymore
    del qbo_nodes_serial

    # importing world with any order but nicer to maintain order
    # second life expects it, which isn't to spec.
    qbo_nodes_list = sorted_nodes(qbo_nodes)

    qbo_frame_counter = 0
    while lineIdx < len(file_lines):
        line = file_lines[lineIdx]

        # End of the previous motion. Begin the animation section of the file with
        # the following header.
        #  MOTION
        #  Frames: n
        #  Frame Time: dt
        if len(line) > 0 and line[0].lower() == 'motion':
            lineIdx += 1  # Read frame count.
            line = file_lines[lineIdx]
            if (
                    len(line) == 2 and
                    line[0].lower() == 'frames:'
            ):
                qbo_frame_count = int(line[1])

            lineIdx += 1  # Read frame rate.
            line = file_lines[lineIdx]
            if (
                    len(line) == 3 and
                    line[0].lower() == 'frame' and
                    line[1].lower() == 'time:'
            ):
                qbo_frame_time = float(line[2])

            lineIdx += 1  # Set the cursor to the first frame
            line = file_lines[lineIdx]

            qbo_frame_counter = 0
            for name in qbo_nodes:
                qbo_node = qbo_nodes[name]
                qbo_node.anim_data = [(0, 0, 0, 0, 0, 0, 0)]

        if len(line) == 0:
            break

        if qbo_frame_counter >= qbo_frame_count:
            continue

        for qbo_node in qbo_nodes_list:
            # for qbo_node in qbo_nodes_serial:
            lx = ly = lz = rx = ry = rz = rw = 0.0
            channels = qbo_node.channels
            anim_data = qbo_node.anim_data
            if channels[0] != -1:
                lx = float(line[channels[0]])

            if channels[1] != -1:
                ly = float(line[channels[1]])

            if channels[2] != -1:
                lz = float(line[channels[2]])

            if channels[3] != -1 or channels[4] != -1 or channels[5] != -1 or channels[6] != -1:

                rx = float(line[channels[3]])
                ry = float(line[channels[4]])
                rz = float(line[channels[5]])
                rw = float(line[channels[6]])

            # Done importing motion data #
            anim_data.append((lx, ly, lz, rx, ry, rz, rw))
        lineIdx += 1
        qbo_frame_counter += 1

    # Assign children
    for qbo_node in qbo_nodes_list:
        qbo_node_parent = qbo_node.parent
        if qbo_node_parent:
            qbo_node_parent.children.append(qbo_node)

    # Now set the tip of each qbo_node
    for qbo_node in qbo_nodes_list:

        if not qbo_node.rest_tail_world:
            if len(qbo_node.children) == 0:
                # could just fail here, but rare QBO files have childless nodes
                qbo_node.rest_tail_world = Vector(qbo_node.rest_head_world)
                qbo_node.rest_tail_local = Vector(qbo_node.rest_head_local)
            elif len(qbo_node.children) == 1:
                qbo_node.rest_tail_world = Vector(qbo_node.children[0].rest_head_world)
                qbo_node.rest_tail_local = qbo_node.rest_head_local + qbo_node.children[0].rest_head_local
            else:
                # allow this, see above
                # if not qbo_node.children:
                #     raise Exception("qbo node has no end and no children. bad file")

                # Removed temp for now
                rest_tail_world = Vector((0.0, 0.0, 0.0))
                rest_tail_local = Vector((0.0, 0.0, 0.0))
                for qbo_node_child in qbo_node.children:
                    rest_tail_world += qbo_node_child.rest_head_world
                    rest_tail_local += qbo_node_child.rest_head_local

                qbo_node.rest_tail_world = rest_tail_world * (1.0 / len(qbo_node.children))
                qbo_node.rest_tail_local = rest_tail_local * (1.0 / len(qbo_node.children))

        # Make sure tail isn't the same location as the head.
        if (qbo_node.rest_tail_local - qbo_node.rest_head_local).length <= EPSILON:
            print("\tzero length node found:", qbo_node.name)
            qbo_node.rest_tail_local.y = qbo_node.rest_tail_local.y + (1.0 / 10.0)
            qbo_node.rest_tail_world.y = qbo_node.rest_tail_world.y + (1.0 / 10.0)

    # Reopen the file for reimporting
    file.close()
    file = open(file_path, 'r')

    # Separate into a list of lists, each line a list of words.
    file_lines = file.readlines()
    # Non standard carriage returns?
    if len(file_lines) == 1:
        file_lines = file_lines[0].split('\r')
    if len(file_lines) <= lineIdx:
        return qbo_nodes, qbo_frame_time, qbo_frame_count
    file_lines = file_lines[lineIdx:]
    file.close()
    file = open(file_path + ".obj", "w")
    weights = {}
    vertices = {}
    vertex_index = 1
    qbo_name = ""
    for line in file_lines:
        if line.strip().startswith("o "):
            qbo_name = line.strip()[1:].strip()
            vertex_index = 1
        elif line.strip().startswith("v "):
            if not qbo_name in vertices:
                vertices[qbo_name] = {}
            vertices[qbo_name][vertex_index] = [float(v.strip()) for v in line.strip()[1:].strip().split()]
            line = [str(v) for v in vertices[qbo_name][vertex_index]]
            vertex_index += 1
            if len(line) < 3:
                continue
            line = line[:3]
            vertices[qbo_name][vertex_index - 1] = vertices[qbo_name][vertex_index - 1][:3]
            logger.debug(str(vertex_index - 1) + " = " + str(line))
            file.write("v " + " ".join(line) + "\n")
            continue
        elif line.strip().startswith("vw "):
            weight = line.strip()[2:].strip().split()
            logger.debug(str(weight))
            if len(weight) < 3:
                continue
            vertex = int(weight[0])
            weight = weight[1:]
            if len(weight) % 2 != 0:
                continue
            if not qbo_name in weights:
                weights[qbo_name] = {}
            if not vertex in weights[qbo_name]:
                weights[qbo_name][vertex] = {}
            index = 0
            while index < len(weight):
                logger.debug(weight[index] + " -> " + weight[index + 1])
                weights[qbo_name][vertex][weight[index]] = float(weight[index + 1])
                index += 2
            continue
        file.write(line.strip() + "\n")
    file.close()

    return qbo_nodes, qbo_frame_time, qbo_frame_count, vertices, weights


def qbo_node_dict2armature(
        context,
        qbo_name,
        qbo_nodes,
        qbo_frame_time,
        frame_start=1,
        IMPORT_LOOP=False,
        use_fps_scale=False,
):

    if frame_start < 1:
        frame_start = 1

    # Add the new armature,
    scene = context.scene
    for obj in scene.objects:
        obj.select_set(False)

    arm_data = bpy.data.armatures.new(qbo_name)
    arm_ob = bpy.data.objects.new(qbo_name, arm_data)

    context.collection.objects.link(arm_ob)

    arm_ob.select_set(True)
    context.view_layer.objects.active = arm_ob

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    qbo_nodes_list = sorted_nodes(qbo_nodes)

    # Get the average bone length for zero length bones, we may not use this.
    average_bone_length = 0.0
    nonzero_count = 0
    for qbo_node in qbo_nodes_list:
        l = (qbo_node.rest_head_local - qbo_node.rest_tail_local).length
        if l:
            average_bone_length += l
            nonzero_count += 1

    # Very rare cases all bones could be zero length???
    if not average_bone_length:
        average_bone_length = 0.1
    else:
        # Normal operation
        average_bone_length = average_bone_length / nonzero_count

    # XXX, annoying, remove bone.
    while arm_data.edit_bones:
        arm_ob.edit_bones.remove(arm_data.edit_bones[-1])

    ZERO_AREA_BONES = []
    for qbo_node in qbo_nodes_list:

        # New editbone
        bone = qbo_node.temp = arm_data.edit_bones.new(qbo_node.name)

        bone.head = qbo_node.rest_head_world
        bone.tail = qbo_node.rest_tail_world

        # Zero Length Bones! (an exceptional case)
        if (bone.head - bone.tail).length < EPSILON:
            print("\tzero length bone found:", bone.name)
            if qbo_node.parent:
                ofs = qbo_node.parent.rest_head_local - qbo_node.parent.rest_tail_local
                if ofs.length:  # is our parent zero length also?? unlikely
                    bone.tail = bone.tail - ofs
                else:
                    bone.tail.y = bone.tail.y + average_bone_length
            else:
                bone.tail.y = bone.tail.y + average_bone_length

            ZERO_AREA_BONES.append(bone.name)

    for qbo_node in qbo_nodes_list:
        if qbo_node.parent:
            # qbo_node.temp is the Editbone

            # Set the bone parent
            qbo_node.temp.parent = qbo_node.parent.temp

            # Set the connection state
            if (
                    (not qbo_node.has_loc) and
                    (qbo_node.parent.temp.name not in ZERO_AREA_BONES) and
                    (qbo_node.parent.rest_tail_local == qbo_node.rest_head_local)
            ):
                qbo_node.temp.use_connect = True

    # Replace the editbone with the editbone name,
    # to avoid memory errors accessing the editbone outside editmode
    for qbo_node in qbo_nodes_list:
        qbo_node.temp = qbo_node.temp.name

    # Now Apply the animation to the armature

    # Get armature animation data
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    pose = arm_ob.pose
    pose_bones = pose.bones

    context.view_layer.update()

    arm_ob.animation_data_create()
    action = bpy.data.actions.new(name=qbo_name)
    arm_ob.animation_data.action = action

    # Replace the qbo_node.temp (currently an editbone)
    # With a tuple  (pose_bone, armature_bone, bone_rest_matrix, bone_rest_matrix_inv)
    num_frame = 0
    for qbo_node in qbo_nodes_list:
        bone_name = qbo_node.temp  # may not be the same name as the qbo_node, could have been shortened.
        pose_bone = pose_bones[bone_name]
        rest_bone = arm_data.bones[bone_name]
        bone_rest_matrix = rest_bone.matrix_local.to_3x3()

        bone_rest_matrix_inv = Matrix(bone_rest_matrix)
        bone_rest_matrix_inv.invert()

        bone_rest_matrix_inv.resize_4x4()
        bone_rest_matrix.resize_4x4()
        qbo_node.temp = (pose_bone, bone, bone_rest_matrix, bone_rest_matrix_inv)

        if 0 == num_frame:
            num_frame = len(qbo_node.anim_data)

    # Choose to skip some frames at the beginning. Frame 0 is the rest pose
    # used internally by this importer. Frame 1, by convention, is also often
    # the rest pose of the skeleton exported by the motion capture system.
    skip_frame = 1
    if num_frame > skip_frame:
        num_frame = num_frame - skip_frame

    # Create a shared time axis for all animation curves.
    time = [float(frame_start)] * num_frame
    if use_fps_scale:
        dt = scene.render.fps * qbo_frame_time
        for frame_i in range(1, num_frame):
            time[frame_i] += float(frame_i) * dt
    else:
        for frame_i in range(1, num_frame):
            time[frame_i] += float(frame_i)

    # print("qbo_frame_time = %f, dt = %f, num_frame = %d"
    #      % (qbo_frame_time, dt, num_frame]))

    for i, qbo_node in enumerate(qbo_nodes_list):
        pose_bone, bone, bone_rest_matrix, bone_rest_matrix_inv = qbo_node.temp

        if qbo_node.has_loc:
            # Not sure if there is a way to query this or access it in the
            # PoseBone structure.
            data_path = 'pose.bones["%s"].location' % pose_bone.name

            location = [(0.0, 0.0, 0.0)] * num_frame
            for frame_i in range(num_frame):
                qbo_loc = qbo_node.anim_data[frame_i + skip_frame][:3]

                bone_translate_matrix = Matrix.Translation(
                    Vector(qbo_loc) - qbo_node.rest_head_local)
                location[frame_i] = (bone_rest_matrix_inv @
                                     bone_translate_matrix).to_translation()

            # For each location x, y, z.
            for axis_i in range(3):
                curve = action.fcurves.new(data_path=data_path, index=axis_i, action_group=qbo_node.name)
                keyframe_points = curve.keyframe_points
                keyframe_points.add(num_frame)

                for frame_i in range(num_frame):
                    keyframe_points[frame_i].co = (
                        time[frame_i],
                        location[frame_i][axis_i],
                    )

        if qbo_node.has_rot:
            rotate = [(1.0, 0.0, 0.0, 0.0)] * num_frame
            data_path = ('pose.bones["%s"].rotation_quaternion' % pose_bone.name)

            for frame_i in range(num_frame):
                qbo_rot = list(qbo_node.anim_data[frame_i + skip_frame][3:])
                qbo_rot = [qbo_rot[len(qbo_rot) - 1]] + qbo_rot[:(len(qbo_rot) - 1)] 

                # apply rotation order.
                quat = Quaternion(tuple(qbo_rot))
                bone_rotation_matrix = quat.to_matrix().to_4x4()
                bone_rotation_matrix = (
                    bone_rest_matrix_inv @
                    bone_rotation_matrix @
                    bone_rest_matrix
                )

                rotate[frame_i] = bone_rotation_matrix.to_quaternion()

            # For each quaternion w, x, y, z.
            for axis_i in range(len(rotate[0])):
                curve = action.fcurves.new(data_path=data_path, index=axis_i, action_group=qbo_node.name)
                keyframe_points = curve.keyframe_points
                keyframe_points.add(num_frame)

                for frame_i in range(num_frame):
                    keyframe_points[frame_i].co = (
                        time[frame_i],
                        rotate[frame_i][axis_i],
                    )

    for cu in action.fcurves:
        if IMPORT_LOOP:
            pass  # 2.5 doenst have cyclic now?

        for bez in cu.keyframe_points:
            bez.interpolation = 'LINEAR'

    return arm_ob


def load(
        context,
        filepath,
        *,
        use_cyclic=False,
        frame_start=1,
        use_fps_scale=False,
        update_scene_fps=False,
        update_scene_duration=False,
        report=print,
):
    logger = logging.getLogger(__name__)
    t1 = time.time()
    now = datetime.now()

    log_path = bpy.path.abspath(filepath + ".log")
    log_handler = logging.FileHandler(log_path)
    #logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)
    logger.debug(now.strftime("%d-%m-%Y@%H:%M:%S"))
    logger.debug("\tparsing qbo %r..." % filepath)
    qbo_nodes, qbo_frame_time, qbo_frame_count, qbo_vertices, qbo_weights = read_qbo(
        logger, context, filepath,
    )
    #open(filepath + ".json", "w").write(json.dumps(qbo_weights))

    logger.debug("%.4f" % (time.time() - t1))

    scene = context.scene
    frame_orig = scene.frame_current

    # Broken QBO handling: guess frame rate when it is not contained in the file.
    if qbo_frame_time is None:
        report(
            {'WARNING'},
            "The QBO file does not contain frame duration in its MOTION "
            "section, assuming the QBO and Blender scene have the same "
            "frame rate"
        )
        qbo_frame_time = scene.render.fps_base / scene.render.fps
        # No need to scale the frame rate, as they're equal now anyway.
        use_fps_scale = False

    if update_scene_fps:
        _update_scene_fps(context, report, qbo_frame_time)

        # Now that we have a 1-to-1 mapping of Blender frames and QBO frames, there is no need
        # to scale the FPS any more. It's even better not to, to prevent roundoff errors.
        use_fps_scale = False

    if update_scene_duration:
        _update_scene_duration(context, report, qbo_frame_count, qbo_frame_time, frame_start, use_fps_scale)

    t1 = time.time()
    logger.debug("\timporting to blender...")

    qbo_name = bpy.path.display_name_from_filepath(filepath)

    try:
        bpy.ops.wm.obj_import(filepath=filepath + ".obj")
    except:
        bpy.ops.import_scene.obj(filepath=filepath + ".obj")
    try:
        os.remove(filepath + ".obj")
    except:
        pass
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.object.select_by_type(type="MESH")
    meshes = []
    for mesh in context.selected_objects:
        meshes.append(mesh)
    bpy.ops.object.select_all(action="DESELECT")
    for mesh in meshes:
        if not mesh.name in qbo_weights:
            #logger.debug(mesh.name)
            continue
        if not mesh.name in qbo_vertices:
            #logger.debug(mesh.name)
            continue
        mesh.select_set(True)
        for name in qbo_nodes:
            group = mesh.vertex_groups.new(name=name)
            vertices = mesh.data.vertices
            for vertex in vertices:
                for index in qbo_weights[mesh.name]:
                    #logger.debug(str(index) + " ? " + str(list(qbo_vertices[mesh.name].keys())))
                    if not index in qbo_vertices[mesh.name]:
                        continue
                    if get_distance(qbo_vertices[mesh.name][index], list(tuple(vertex.co))) > EPSILON:
                        continue
                    if not name in qbo_weights[mesh.name][index]:
                        continue
                    weight = qbo_weights[mesh.name][index][name]
                    group.add([vertex.index], weight, "REPLACE")
                    #logger.debug(str(vertex.index) + " -> " + name + " @ " + mesh.name)
        bpy.ops.object.select_all(action="DESELECT")

    armature = qbo_node_dict2armature(
        context, qbo_name, qbo_nodes, qbo_frame_time,
        frame_start=frame_start,
        IMPORT_LOOP=use_cyclic,
        use_fps_scale=use_fps_scale,
    )

    for mesh in meshes:
        mesh.select_set(True)
        armature.select_set(True)
        bpy.ops.object.parent_set(type='ARMATURE')
        bpy.ops.object.select_all(action="DESELECT")

    logger.debug('Done in %.4f\n' % (time.time() - t1))

    context.scene.frame_set(frame_orig)

    return {'FINISHED'}


def _update_scene_fps(context, report, qbo_frame_time):
    """Update the scene's FPS settings from the QBO, but only if the QBO contains enough info."""

    # Broken QBO handling: prevent division by zero.
    if qbo_frame_time == 0.0:
        report(
            {'WARNING'},
            "Unable to update scene frame rate, as the QBO file "
            "contains a zero frame duration in its MOTION section",
        )
        return

    scene = context.scene
    scene_fps = scene.render.fps / scene.render.fps_base
    new_fps = 1.0 / qbo_frame_time

    if scene.render.fps != new_fps or scene.render.fps_base != 1.0:
        print("\tupdating scene FPS (was %f) to QBO FPS (%f)" % (scene_fps, new_fps))
    scene.render.fps = int(round(new_fps))
    scene.render.fps_base = scene.render.fps / new_fps


def _update_scene_duration(
        context, report, qbo_frame_count, qbo_frame_time, frame_start,
        use_fps_scale):
    """Extend the scene's duration so that the QBO file fits in its entirety."""

    if qbo_frame_count is None:
        report(
            {'WARNING'},
            "Unable to extend the scene duration, as the QBO file does not "
            "contain the number of frames in its MOTION section",
        )
        return

    # Not likely, but it can happen when a QBO is just used to store an armature.
    if qbo_frame_count == 0:
        return

    if use_fps_scale:
        scene_fps = context.scene.render.fps / context.scene.render.fps_base
        scaled_frame_count = int(ceil(qbo_frame_count * qbo_frame_time * scene_fps))
        qbo_last_frame = frame_start + scaled_frame_count
    else:
        qbo_last_frame = frame_start + qbo_frame_count

    # Only extend the scene, never shorten it.
    if context.scene.frame_end < qbo_last_frame:
        context.scene.frame_end = qbo_last_frame
