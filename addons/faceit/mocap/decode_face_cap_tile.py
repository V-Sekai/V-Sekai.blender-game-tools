
import struct
from typing import Tuple


class ParseError(Exception):
    '''Base exception for when a datagram parsing error occurs.'''


class BuildError(Exception):
    '''Base exception for when a datagram building error occurs.'''


# Constant for special ntp datagram sequences that represent an immediate time.
IMMEDIATELY = 0
# Datagram length in bytes for types that have a fixed size.
_INT_DGRAM_LEN = 4
_FLOAT_DGRAM_LEN = 4
# Strings and blob dgram length is always a multiple of 4 bytes.
_STRING_DGRAM_PAD = 4
_EMPTY_STR_DGRAM = b'\x00\x00\x00\x00'


def get_string(dgram: bytes, start_index: int) -> Tuple[str, int]:
    """Get a python string from the datagram, starting at pos start_index.
    According to the specifications, a string is:
    "A sequence of non-null ASCII characters followed by a null,
    followed by 0-3 additional null characters to make the total number
    of bits a multiple of 32".
    Args:
    dgram: A datagram packet.
    start_index: An index where the string starts in the datagram.
    Returns:
    A tuple containing the string and the new end index.
    Raises:
    ParseError if the datagram could not be parsed.
    """
    if start_index < 0:
        raise ParseError('start_index < 0')
    offset = 0
    try:
        if (len(dgram) > start_index + _STRING_DGRAM_PAD and
                dgram[start_index + _STRING_DGRAM_PAD] == _EMPTY_STR_DGRAM):
            return '', start_index + _STRING_DGRAM_PAD
        while dgram[start_index + offset] != 0:
            offset += 1
        # Align to a byte word.
        if (offset) % _STRING_DGRAM_PAD == 0:
            offset += _STRING_DGRAM_PAD
        else:
            offset += (-offset % _STRING_DGRAM_PAD)
        # Python slices do not raise an IndexError past the last index,
        # do it ourselves.
        if offset > len(dgram[start_index:]):
            raise ParseError('Datagram is too short')
        data_str = dgram[start_index:start_index + offset]
        return data_str.replace(b'\x00', b'').decode('utf-8'), start_index + offset
    except IndexError as ie:
        raise ParseError('Could not parse datagram %s' % ie)
    except TypeError as te:
        raise ParseError('Could not parse datagram %s' % te)


def get_int(dgram: bytes, start_index: int) -> Tuple[int, int]:
    """Get a 32-bit big-endian two's complement integer from the datagram.
    Args:
    dgram: A datagram packet.
    start_index: An index where the integer starts in the datagram.
    Returns:
    A tuple containing the integer and the new end index.
    Raises:
    ParseError if the datagram could not be parsed.
    """
    try:
        if len(dgram[start_index:]) < _INT_DGRAM_LEN:
            raise ParseError('Datagram is too short')
        return (
            struct.unpack('>i',
                          dgram[start_index:start_index + _INT_DGRAM_LEN])[0],
            start_index + _INT_DGRAM_LEN)
    except (struct.error, TypeError) as e:
        raise ParseError('Could not parse datagram %s' % e)


def get_float(dgram: bytes, start_index: int) -> Tuple[float, int]:
    """Get a 32-bit big-endian IEEE 754 floating point number from the datagram.
    Args:
    dgram: A datagram packet.
    start_index: An index where the float starts in the datagram.
    Returns:
    A tuple containing the float and the new end index.
    Raises:
    ParseError if the datagram could not be parsed.
    """
    try:
        if len(dgram[start_index:]) < _FLOAT_DGRAM_LEN:
            # Noticed that Reaktor doesn't send the last bunch of \x00 needed to make
            # the float representation complete in some cases, thus we pad here to
            # account for that.
            dgram = dgram + b'\x00' * (_FLOAT_DGRAM_LEN - len(dgram[start_index:]))
        return (
            struct.unpack('>f',
                          dgram[start_index:start_index + _FLOAT_DGRAM_LEN])[0],
            start_index + _FLOAT_DGRAM_LEN)
    except (struct.error, TypeError) as e:
        raise ParseError('Could not parse datagram %s' % e)


def decode_face_cap_tile(dgram) -> Tuple[str, list]:

    _dgram = dgram
    _parameters = []

    try:
        _address_regexp, index = get_string(_dgram, 0)
        if not _dgram[index:]:
            # No params is legit, just return now.
            return

        # Get the parameters types.
        type_tag, index = get_string(_dgram, index)
        if type_tag.startswith(','):
            type_tag = type_tag[1:]

        params = []
        param_stack = [params]
        # Parse each parameter given its type.
        for param in type_tag:
            if param == "i":  # Integer.
                val, index = get_int(_dgram, index)
            elif param == "f":  # Float.
                val, index = get_float(_dgram, index)
            elif param == "s":  # String.
                val, index = get_string(_dgram, index)
            elif param == "T":  # True.
                val = True
            elif param == "F":  # False.
                val = False
            elif param == "[":  # Array start.
                array = []
                param_stack[-1].append(array)
                param_stack.append(array)
            elif param == "]":  # Array stop.
                if len(param_stack) < 2:
                    raise ParseError('Unexpected closing bracket in type tag: {0}'.format(type_tag))
                param_stack.pop()
            # TODO: Support more exotic types as described in the specification.
            else:
                continue
            if param not in "[]":
                param_stack[-1].append(val)
        if len(param_stack) != 1:
            raise ParseError('Missing closing bracket in type tag: {0}'.format(type_tag))
        _parameters = params
        return (_address_regexp, params)
    except ParseError as pe:
        raise ParseError('Found incorrect datagram, ignoring it', pe)

# /W [31, 0.0]
# /W [33, 0.1455814391374588]
# /HT [0.6953338384628296, -18.356565475463867, -43.202964782714844]
# /HR [-60.31721496582031, -2.2959725856781006, -3.5035483837127686]
# /HRQ [-0.5025894045829773, -0.0019598761573433876, -0.036486901342868805, 0.8637527823448181]
# /ELR [10.877311706542969, -5.366491317749023]
# /ERR [10.930986404418945, -1.939971685409546]
