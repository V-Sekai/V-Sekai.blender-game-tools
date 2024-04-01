import struct


def decode_live_link_face(bytes_data: bytes):
    """ Decodes the given bytes (send from a PyLiveLinkFace App)
    Returns only the motion capture data (61 floats), 
    None otherwise.
    Thanks to Jim West for creating the PyLiveLinkFace project: https://github.com/JimWest/PyLiveLinkFace
    """
    # version = struct.unpack('<i', bytes_data[0:4])[0]
    # uuid = bytes_data[4:41].decode("utf-8")
    name_length = struct.unpack('!i', bytes_data[41:45])[0]
    name_end_pos = 45 + name_length
    # name = bytes_data[45:name_end_pos].decode("utf-8")
    data = None
    if len(bytes_data) > name_end_pos + 16:
        # FFrameTime, FFrameRate and data length
        _frame_number, _sub_frame, _fps, _denominator, data_length = struct.unpack(
            "!if2ib", bytes_data[name_end_pos:name_end_pos + 17])
        if data_length != 61:
            raise ValueError(
                f'Blend shape length is {data_length} but should be 61, something is wrong with the data.')
        data = struct.unpack(
            "!61f", bytes_data[name_end_pos + 17:])
    if data:
        return convert_live_link_face_to_face_cap_format(data)


def convert_live_link_face_to_face_cap_format(data):
    '''Converts the data from the PyLiveLinkFace App to the Face Cap format (used in faceit).'''
    animation_data = []
    for i, x in enumerate(data):
        if i < 52:
            animation_data.append(('/W', (i, x)))
        else:
            break
    # append head_rotation_data
    # animation_data.append(('/HR', data[52:55]))
    animation_data.append(('/HR', [-data[53], -data[52], -data[54]]))
    # append eye_left_rotation_data
    animation_data.append(('/ELR', [data[56], data[55], 0.0])) # strip roll, otherwise 55:58
    # Yaw, Pitch, Roll...
    # roll can be discarded...
    # append eye_right_rotation_data
    animation_data.append(('/ERR', [data[59], data[58], 0.0])) # strip roll, otherwise 58:61
    return animation_data
