# helper utilitilies to support Audio Preview -- humbletim 2021.12.14

import bpy
import aud

class RuntimeComponent:
    """
    container for associating non-persistant python values to blender objects at RuntimeComponent
    """
    @classmethod
    def hash(cls, object):
        return str(object.as_pointer())

    @staticmethod
    def object_query(haystack, attr, needle):
        """
        usage: result = object_query(bpy.data.objects, 'attribute_name', attribute_value)
        """
        if needle is None: return None
        id = RuntimeComponent.hash(needle)
        return [c for c in haystack if RuntimeComponent.hash(getattr(c, attr, None)) == id][0]

    def __init__(self):
        self.map = {}
    def get(self, pair, defaultValue=None):
        return self.map.get(self.hash(pair), defaultValue)
    def remove(self, pair):
        return self.set(pair, None)
    def set(self, pair, sound):
        id = self.hash(pair)
        cur = self.map.get(id, None)
        self.map[id] = sound
        return cur

class AudioPlayback:
    handles = RuntimeComponent()
    def isPlaying(self):
        return AudioPlayback.handles.get(self)
    def togglePlayback(self):
        if self.isPlaying():
            self.stop()
        else:
            self.play()
    def play(self):
        object = RuntimeComponent.object_query(bpy.data.objects, 'OMI_audio_pair', self)
        cam = bpy.data.objects["Camera"]
        device = aud.Device()
        device.listener_location = cam.location
        device.listener_orientation = cam.rotation_quaternion
        print("PLAYING", object, self.source, self.emitter)
        sound = aud.Sound(self.source.filename)
        handle = device.play(sound)
        handle.volume = self.emitter.gain
        handle.location = object.location
        handle.orientation = object.rotation_quaternion
        AudioPlayback.handles.set(self, handle)
    def stop(self):
        handle = AudioPlayback.handles.remove(self)
        if handle:
            handle.stop()

def json_serializable(cls):
    def as_dict(self):
        yield OrderedDict(
            (name, value) for name, value in zip(
                self._fields,
                iter(super(cls, self).__iter__())))
    cls.__iter__ = as_dict
    return cls

