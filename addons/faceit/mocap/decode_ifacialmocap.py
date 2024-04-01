# https://www.ifacialmocap.com/for-developer/

from operator import itemgetter


def decode_ifacial_mocap(data, shape_reference):
    return convert_ifacial_mocap_to_face_cap_format(data.decode('utf-8'), shape_reference)


def convert_ifacial_mocap_to_face_cap_format(data, shape_reference):
    data = data.split('|')
    animation_data = []
    input_shapes = {shape.split('-')[0]: float(shape.split('-')[1]) /
                    100 for shape in data[:54]}
    for i, shape_name in enumerate(shape_reference):
        value = input_shapes.get(shape_name, 0)  # Default to 0 if shape_name not found
        animation_data.append(('/W', (i, value)))
    head_data = data[54].split('#')[1].split(',')
    head_rotation = head_data[:3]
    animation_data.append(('/HR', [float(i) for i in head_rotation]))
    head_translation = head_data[3:]
    animation_data.append(('/HT', [float(i) for i in head_translation]))
    eye_left_data = data[55].split('#')[1].split(',')
    animation_data.append(('/ELR', [float(i) for i in eye_left_data]))
    eye_right_data = data[56].split('#')[1].split(',')
    animation_data.append(('/ERR', [float(i) for i in eye_right_data]))
    return animation_data
