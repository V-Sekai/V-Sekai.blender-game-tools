from typing import Tuple
from math import hypot, sqrt, acos, radians, degrees, dist
import numpy as np


def clamp(value: float or int, min_value: float or int = 0.0, max_value: float or int = 1.0) -> float or int:
    return min(max(value, min_value), max_value)

def map_value(val: float, src: Tuple[float, float], dst: Tuple[float, float] = (0.0, 1.0)):
    """
    Scale the given value from the scale of src to the scale of dst.
    """
    return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]

def direction(_p1, _p2, _norm=True):
    if _norm:
        return (_p1 - _p2).normalized()
    else:
        return _p1 - _p2

def dotproduct(v1, v2):
    return sum((a*b) for a, b in zip(v1, v2))

def length(v):
    return sqrt(dotproduct(v, v))

def angle_between(v1, v2, as_degrees: bool = True):
    a = acos(dotproduct(v1, v2) / (length(v1) * length(v2)))
    return degrees(a) if as_degrees else a

def distance_between(_p1, _p2):
    return dist(_p1, _p2) # hypot(_p1[0] - _p2[0], _p1[1] - _p2[1])
    #return math.sqrt((_p1[1] - _p1[0])**2 + (_p2[1] - _p2[0])**2)

def lineseg_dist(p, a, b):
    # normalized tangent vector
    d = np.divide(b - a, np.linalg.norm(b - a))

    # signed parallel distance components
    s = np.dot(a - p, d)
    t = np.dot(p - b, d)

    # clamped parallel distance
    h = np.maximum.reduce([s, t, 0])

    # perpendicular distance component
    c = np.cross(p - a, d)

    return np.hypot(h, np.linalg.norm(c))
